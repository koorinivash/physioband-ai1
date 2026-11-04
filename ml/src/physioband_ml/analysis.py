"""Session analysis: the single entry point used by the FastAPI backend.

    raw samples -> validation -> resampling -> calibration -> filtering
                -> elbow kinematics -> repetition counting -> features
                -> Random Forest quality classification -> feedback
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from physioband_ml.config import (
    FEEDBACK_MESSAGES,
    LABEL_CORRECT,
    LABEL_DISPLAY,
    LABEL_INCOMPLETE,
    LABEL_IRREGULAR,
    LABEL_TOO_FAST,
    LABEL_UNCLASSIFIED,
    SUPPORTED_EXERCISES,
    CalibrationConfig,
    PipelineConfig,
)
from physioband_ml.feature_extraction import extract_rep_features
from physioband_ml.models.predictor import QualityModel
from physioband_ml.repetition_counting import detect_repetitions
from physioband_ml.segmentation import ProcessedSignals, process_frame


class UnsupportedExerciseError(ValueError):
    pass


@dataclass
class RepResult:
    number: int
    start_timestamp_ms: float
    end_timestamp_ms: float
    duration_s: float
    rom_deg: float
    avg_force_n: float
    peak_force_n: float
    label: str
    label_display: str
    confidence: float | None
    probabilities: dict[str, float] | None
    feedback: str
    features: dict[str, float] | None = None


@dataclass
class LiveStatus:
    movement_phase: str          # lifting / lowering / holding / resting
    upper_arm_status: str        # stable / moving / excessive_swing
    forearm_status: str          # active / still
    current_angle_deg: float
    current_force_n: float
    upper_arm_swing_deg: float


@dataclass
class SessionAnalysis:
    exercise_id: str
    sample_count: int
    duration_s: float
    total_reps: int
    correct_reps: int
    incorrect_reps: int
    incomplete_reps: int
    too_fast_reps: int
    irregular_reps: int
    unclassified_reps: int
    quality_score: float | None
    avg_tension_n: float | None
    peak_tension_n: float | None
    classification_available: bool
    reps: list[RepResult]
    live: LiveStatus | None
    suggestions: list[str]
    validation: dict[str, Any]
    processing_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _live_status(sig: ProcessedSignals) -> LiveStatus:
    fs = sig.sample_rate_hz
    window = max(2, int(fs * 1.0))
    vel = sig.elbow_velocity[-window:]
    mean_vel = float(np.mean(vel))
    if mean_vel > 20:
        phase = "lifting"
    elif mean_vel < -20:
        phase = "lowering"
    elif sig.elbow_angle[-1] > 45:
        phase = "holding"
    else:
        phase = "resting"

    swing_window = sig.ua_swing[-max(2, int(fs * 2.0)) :]
    swing_range = float(np.ptp(swing_window))
    if swing_range > 20:
        ua_status = "excessive_swing"
    elif swing_range > 8:
        ua_status = "moving"
    else:
        ua_status = "stable"

    fa_gyro = np.linalg.norm(sig.fa[-window:, 3:6], axis=1)
    fa_status = "active" if float(fa_gyro.mean()) > 15 else "still"

    return LiveStatus(
        movement_phase=phase,
        upper_arm_status=ua_status,
        forearm_status=fa_status,
        current_angle_deg=round(float(sig.elbow_angle[-1]), 1),
        current_force_n=round(float(sig.force[-1]), 2),
        upper_arm_swing_deg=round(swing_range, 1),
    )


def build_suggestions(counts: Counter, total: int, classified: bool) -> list[str]:
    if total == 0:
        return ["No complete repetitions were detected. Perform full, controlled curls from full extension."]
    if not classified:
        return ["Repetitions were counted, but quality classification was unavailable for this session."]
    tips = []
    if counts[LABEL_INCOMPLETE]:
        tips.append("Use the full range of motion: lower until the elbow is straight and curl until the forearm is near vertical.")
    if counts[LABEL_TOO_FAST]:
        tips.append("Slow the tempo: take roughly 2 seconds to lift and 2 seconds to lower.")
    if counts[LABEL_IRREGULAR]:
        tips.append("Keep the movement smooth and keep the upper arm close to the body without swinging.")
    if not tips:
        tips.append("Excellent consistency. Maintain this tempo and range in your next session.")
    return tips


def analyze_frame(
    df: pd.DataFrame,
    exercise_id: str = "biceps_curl",
    model: QualityModel | None = None,
    cfg: PipelineConfig | None = None,
    calib: CalibrationConfig | None = None,
    live: bool = False,
    include_features: bool = False,
) -> SessionAnalysis:
    if exercise_id not in SUPPORTED_EXERCISES:
        raise UnsupportedExerciseError(f"Exercise '{exercise_id}' is not supported yet")

    # Inference must use the same configuration the model was trained with.
    cfg = cfg or (model.pipeline_config if model else PipelineConfig())
    sig = process_frame(df, cfg, calib)
    reps = detect_repetitions(sig.elbow_angle, sig.sample_rate_hz, cfg, sig.gap_mask, live=live)

    feature_rows = [extract_rep_features(sig, rep) for rep in reps]
    predictions = model.predict(feature_rows) if model is not None else [None] * len(reps)

    results: list[RepResult] = []
    for rep, feats, pred in zip(reps, feature_rows, predictions):
        label = pred.label if pred else LABEL_UNCLASSIFIED
        force = sig.force[rep.start_idx : rep.end_idx + 1]
        results.append(
            RepResult(
                number=rep.number,
                start_timestamp_ms=round(sig.start_timestamp_ms + rep.start_time_s * 1000.0, 1),
                end_timestamp_ms=round(sig.start_timestamp_ms + rep.end_time_s * 1000.0, 1),
                duration_s=round(rep.duration_s, 3),
                rom_deg=round(rep.rom_deg, 1),
                avg_force_n=round(float(force.mean()), 2),
                peak_force_n=round(float(force.max()), 2),
                label=label,
                label_display=LABEL_DISPLAY.get(label, label),
                confidence=round(pred.confidence, 4) if pred else None,
                probabilities=pred.probabilities if pred else None,
                feedback=FEEDBACK_MESSAGES.get(label, FEEDBACK_MESSAGES[LABEL_UNCLASSIFIED]),
                features={k: round(v, 5) for k, v in feats.items()} if include_features else None,
            )
        )

    counts = Counter(r.label for r in results)
    total = len(results)
    classified_total = total - counts[LABEL_UNCLASSIFIED]
    incorrect = counts[LABEL_INCOMPLETE] + counts[LABEL_TOO_FAST] + counts[LABEL_IRREGULAR]

    if results:
        rep_force = np.concatenate([sig.force[r.start_idx : r.end_idx + 1] for r in reps])
        avg_tension, peak_tension = round(float(rep_force.mean()), 2), round(float(rep_force.max()), 2)
    else:
        avg_tension = peak_tension = None

    notes = []
    if model is None:
        notes.append("No quality model loaded: repetitions are counted but not classified.")
    if sig.gap_mask.any():
        notes.append("Data gaps detected (possible BLE packet loss); repetitions spanning gaps were ignored.")

    return SessionAnalysis(
        exercise_id=exercise_id,
        sample_count=len(sig),
        duration_s=round(float(sig.t[-1]), 2),
        total_reps=total,
        correct_reps=counts[LABEL_CORRECT],
        incorrect_reps=incorrect,
        incomplete_reps=counts[LABEL_INCOMPLETE],
        too_fast_reps=counts[LABEL_TOO_FAST],
        irregular_reps=counts[LABEL_IRREGULAR],
        unclassified_reps=counts[LABEL_UNCLASSIFIED],
        quality_score=round(100.0 * counts[LABEL_CORRECT] / classified_total, 1) if classified_total else None,
        avg_tension_n=avg_tension,
        peak_tension_n=peak_tension,
        classification_available=model is not None,
        reps=results,
        live=_live_status(sig),
        suggestions=build_suggestions(counts, total, model is not None),
        validation=sig.validation.to_dict(),
        processing_notes=notes,
    )
