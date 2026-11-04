"""Sensor calibration support.

The ESP32 already converts raw readings to physical units (g, deg/s, N) using the
load-cell scale factor stored in its configuration. This module applies any
additional per-device correction (gyro bias, accelerometer offset, load-cell
tare offset) and can estimate the gyro bias from a still period.
"""
from __future__ import annotations

import numpy as np

from physioband_ml.config import CalibrationConfig


def apply_calibration(values: np.ndarray, calib: CalibrationConfig) -> np.ndarray:
    """Apply calibration to an ``[n, 13]`` array in SENSOR_CHANNELS order."""
    out = values.copy()
    out[:, 0:3] -= np.asarray(calib.ua_accel_offset, dtype=float)
    out[:, 3:6] -= np.asarray(calib.ua_gyro_bias, dtype=float)
    out[:, 6:9] -= np.asarray(calib.fa_accel_offset, dtype=float)
    out[:, 9:12] -= np.asarray(calib.fa_gyro_bias, dtype=float)
    out[:, 12] = (out[:, 12] - calib.force_offset_n) * calib.force_scale
    return out


def estimate_gyro_bias(values: np.ndarray, still_samples: int) -> CalibrationConfig:
    """Estimate gyro bias from the first ``still_samples`` rows (sensor held still)."""
    still = values[: max(1, still_samples)]
    return CalibrationConfig(
        ua_gyro_bias=still[:, 3:6].mean(axis=0).round(4).tolist(),
        fa_gyro_bias=still[:, 9:12].mean(axis=0).round(4).tolist(),
    )
