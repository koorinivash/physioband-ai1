"""Sensor data validation.

Rows with an unusable timestamp are removed. Individual channel values that are
missing, non-numeric or physically impossible are replaced by NaN so that the
gap-filling step can interpolate them instead of discarding whole samples.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from physioband_ml.config import (
    ACCEL_LIMIT_G,
    FORCE_CHANNEL,
    FORCE_MAX_N,
    FORCE_MIN_N,
    FOREARM_CHANNELS,
    GYRO_LIMIT_DPS,
    SENSOR_CHANNELS,
    TIMESTAMP_COLUMN,
    UPPER_ARM_CHANNELS,
)


class SensorDataError(ValueError):
    """Raised when sensor data cannot be used at all."""


@dataclass
class ValidationReport:
    input_samples: int = 0
    valid_samples: int = 0
    dropped_bad_timestamp: int = 0
    dropped_duplicates: int = 0
    out_of_range_values: int = 0
    missing_values: int = 0
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _limits_for(channel: str) -> tuple[float, float]:
    if channel == FORCE_CHANNEL:
        return FORCE_MIN_N, FORCE_MAX_N
    axis = channel.split("_")[1]
    limit = ACCEL_LIMIT_G if axis.startswith("a") else GYRO_LIMIT_DPS
    return -limit, limit


def validate_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, ValidationReport]:
    """Return a cleaned copy of ``df`` sorted by time, plus a report of what changed."""
    report = ValidationReport(input_samples=len(df))
    required = [TIMESTAMP_COLUMN, *SENSOR_CHANNELS]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise SensorDataError(f"Missing required columns: {', '.join(missing_cols)}")

    out = df.copy()
    out[TIMESTAMP_COLUMN] = pd.to_numeric(out[TIMESTAMP_COLUMN], errors="coerce")
    bad_ts = out[TIMESTAMP_COLUMN].isna() | ~np.isfinite(out[TIMESTAMP_COLUMN].astype(float))
    report.dropped_bad_timestamp = int(bad_ts.sum())
    out = out.loc[~bad_ts]

    before = len(out)
    out = out.sort_values(TIMESTAMP_COLUMN, kind="stable").drop_duplicates(TIMESTAMP_COLUMN, keep="first")
    report.dropped_duplicates = before - len(out)

    for channel in SENSOR_CHANNELS:
        values = pd.to_numeric(out[channel], errors="coerce").astype(float)
        report.missing_values += int(values.isna().sum())
        lo, hi = _limits_for(channel)
        bad = (values < lo) | (values > hi)
        report.out_of_range_values += int(bad.sum())
        out[channel] = values.mask(bad)

    # A sensor that is NaN for the whole recording cannot be interpolated.
    for name, group in (("upper-arm IMU", UPPER_ARM_CHANNELS), ("forearm IMU", FOREARM_CHANNELS)):
        if out[group].isna().all(axis=None):
            report.issues.append(f"No usable {name} data")
    if out[FORCE_CHANNEL].isna().all():
        report.issues.append("No usable load-cell data")

    if report.dropped_duplicates:
        report.issues.append(f"{report.dropped_duplicates} duplicate timestamps removed")
    if report.out_of_range_values:
        report.issues.append(f"{report.out_of_range_values} out-of-range values replaced")

    report.valid_samples = len(out)
    return out.reset_index(drop=True), report
