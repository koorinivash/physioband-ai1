"""Noise filtering.

A zero-phase Butterworth low-pass filter removes vibration and sensor noise while
keeping the 0.2 - 2 Hz content of a resistance-band curl intact. Zero-phase
filtering (sosfiltfilt) avoids shifting peaks in time, which matters for the
repetition counter and duration features.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt


def lowpass(values: np.ndarray, sample_rate_hz: float, cutoff_hz: float, order: int = 4) -> np.ndarray:
    """Low-pass filter along axis 0. Falls back to a moving average for very short input."""
    values = np.asarray(values, dtype=float)
    nyquist = sample_rate_hz / 2.0
    cutoff = min(cutoff_hz, nyquist * 0.95)
    sos = butter(order, cutoff / nyquist, btype="low", output="sos")
    padlen = 3 * (2 * len(sos) + 1)
    if values.shape[0] > padlen:
        return sosfiltfilt(sos, values, axis=0)

    window = max(1, min(5, values.shape[0]))
    kernel = np.ones(window) / window
    if values.ndim == 1:
        return np.convolve(values, kernel, mode="same")
    return np.column_stack([np.convolve(values[:, i], kernel, mode="same") for i in range(values.shape[1])])
