"""End-to-end signal processing: raw samples -> uniform, calibrated, filtered signals.

This single function is used by training (scripts) AND inference (FastAPI) so both
see identical inputs to the repetition counter and feature extractor.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from physioband_ml.config import CalibrationConfig, PipelineConfig
from physioband_ml.preprocessing import (
    ValidationReport,
    apply_calibration,
    lowpass,
    resample_uniform,
    validate_frame,
)
from physioband_ml.preprocessing.validation import SensorDataError
from physioband_ml.segmentation.kinematics import compute_kinematics


@dataclass
class ProcessedSignals:
    t: np.ndarray               # seconds from first sample
    ua: np.ndarray              # [n, 6] filtered upper-arm accel (g) + gyro (deg/s)
    fa: np.ndarray              # [n, 6] filtered forearm accel (g) + gyro (deg/s)
    force: np.ndarray           # [n] filtered band tension (N)
    elbow_angle: np.ndarray     # [n] degrees
    elbow_velocity: np.ndarray  # [n] deg/s
    ua_swing: np.ndarray        # [n] degrees
    gap_mask: np.ndarray        # [n] True inside long data gaps
    sample_rate_hz: float
    start_timestamp_ms: float
    validation: ValidationReport

    def __len__(self) -> int:
        return len(self.t)


MIN_SAMPLES = 10


def process_frame(
    df: pd.DataFrame,
    cfg: PipelineConfig | None = None,
    calib: CalibrationConfig | None = None,
) -> ProcessedSignals:
    cfg = cfg or PipelineConfig()
    calib = calib or CalibrationConfig()

    clean, report = validate_frame(df)
    if len(clean) < MIN_SAMPLES:
        raise SensorDataError(f"Not enough valid samples ({len(clean)}); at least {MIN_SAMPLES} required")

    t, values, gap_mask = resample_uniform(clean, cfg.sample_rate_hz, cfg.max_gap_ms)
    values = apply_calibration(values, calib)
    filtered = lowpass(values, cfg.sample_rate_hz, cfg.lowpass_cutoff_hz, cfg.lowpass_order)

    ua, fa, force = filtered[:, 0:6], filtered[:, 6:12], filtered[:, 12]
    kin = compute_kinematics(ua, fa, cfg.sample_rate_hz, cfg.complementary_alpha)

    return ProcessedSignals(
        t=t,
        ua=ua,
        fa=fa,
        force=force,
        elbow_angle=kin["elbow_angle"],
        elbow_velocity=kin["elbow_velocity"],
        ua_swing=kin["ua_swing"],
        gap_mask=gap_mask,
        sample_rate_hz=cfg.sample_rate_hz,
        start_timestamp_ms=float(clean["timestamp_ms"].iloc[0]),
        validation=report,
    )
