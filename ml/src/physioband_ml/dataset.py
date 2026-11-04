"""Turn labelled raw sensor recordings into a per-repetition feature table.

The SAME processing (`process_frame`), repetition counter and feature extractor
used by the backend are applied here, guaranteeing training/inference parity.
Each detected repetition takes the majority label of the samples it covers, so
both "one label per recorded set" and "per-sample labels" CSVs are supported.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from physioband_ml.config import QUALITY_LABELS, TIMESTAMP_COLUMN, PipelineConfig
from physioband_ml.feature_extraction import extract_rep_features
from physioband_ml.preprocessing.validation import SensorDataError
from physioband_ml.repetition_counting import detect_repetitions
from physioband_ml.segmentation import process_frame

log = logging.getLogger(__name__)


def build_feature_table(raw: pd.DataFrame, cfg: PipelineConfig | None = None) -> pd.DataFrame:
    cfg = cfg or PipelineConfig()
    for col in ("session_id", "label"):
        if col not in raw.columns:
            raise ValueError(f"Training CSV must contain a '{col}' column")
    raw = raw.copy()
    if "participant_id" not in raw.columns:
        raw["participant_id"] = "unknown"
    if "exercise_id" not in raw.columns:
        raw["exercise_id"] = "biceps_curl"

    rows = []
    for session_id, session in raw.groupby("session_id", sort=False):
        session = session.sort_values(TIMESTAMP_COLUMN)
        try:
            sig = process_frame(session, cfg)
        except SensorDataError as exc:
            log.warning("Skipping session %s: %s", session_id, exc)
            continue

        reps = detect_repetitions(sig.elbow_angle, sig.sample_rate_hz, cfg, sig.gap_mask)
        ts = session[TIMESTAMP_COLUMN].to_numpy(dtype=float)
        labels = session["label"].astype(str).to_numpy()
        for rep in reps:
            t0 = sig.start_timestamp_ms + rep.start_time_s * 1000.0
            t1 = sig.start_timestamp_ms + rep.end_time_s * 1000.0
            window = labels[(ts >= t0) & (ts <= t1)]
            window = window[np.isin(window, QUALITY_LABELS)]
            if len(window) == 0:
                continue
            values, counts = np.unique(window, return_counts=True)
            row = extract_rep_features(sig, rep)
            row.update(
                {
                    "participant_id": str(session["participant_id"].iloc[0]),
                    "session_id": str(session_id),
                    "exercise_id": str(session["exercise_id"].iloc[0]),
                    "rep_number": rep.number,
                    "label": str(values[np.argmax(counts)]),
                    "is_synthetic": bool(session["is_synthetic"].astype(bool).any()) if "is_synthetic" in session else False,
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)
