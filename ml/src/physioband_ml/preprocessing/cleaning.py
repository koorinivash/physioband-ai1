"""Missing-value handling and resampling onto a uniform time grid.

BLE packets can be lost or delayed, so samples do not always arrive exactly every
20 ms. All later stages (filtering, peak detection, features) assume a uniform
sample rate, so the data is linearly interpolated onto a fixed grid. Gaps longer
than ``max_gap_ms`` are still interpolated (filters cannot handle NaN) but are
flagged in ``gap_mask`` so repetitions spanning them can be rejected.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from physioband_ml.config import SENSOR_CHANNELS, TIMESTAMP_COLUMN


def resample_uniform(
    df: pd.DataFrame, sample_rate_hz: float, max_gap_ms: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Resample to a uniform grid.

    Returns ``(t_seconds, values[n, 13], gap_mask[n])`` where ``values`` follows the
    column order of :data:`SENSOR_CHANNELS` and ``gap_mask`` is True where the
    sample lies inside a gap longer than ``max_gap_ms``.
    """
    if len(df) < 2:
        raise ValueError("At least two samples are required for resampling")

    ts = df[TIMESTAMP_COLUMN].to_numpy(dtype=float)
    step_ms = 1000.0 / sample_rate_hz
    grid = np.arange(ts[0], ts[-1] + step_ms * 0.5, step_ms)

    values = np.empty((len(grid), len(SENSOR_CHANNELS)), dtype=float)
    for i, channel in enumerate(SENSOR_CHANNELS):
        col = df[channel].to_numpy(dtype=float)
        ok = np.isfinite(col)
        if ok.sum() == 0:
            values[:, i] = 0.0
        elif ok.sum() == 1:
            values[:, i] = col[ok][0]
        else:
            values[:, i] = np.interp(grid, ts[ok], col[ok])

    # Flag grid points that fall inside a long gap between consecutive samples.
    gap_mask = np.zeros(len(grid), dtype=bool)
    diffs = np.diff(ts)
    for idx in np.flatnonzero(diffs > max_gap_ms):
        gap_mask |= (grid > ts[idx]) & (grid < ts[idx + 1])

    t_seconds = (grid - grid[0]) / 1000.0
    return t_seconds, values, gap_mask
