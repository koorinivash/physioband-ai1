"""Repetition counting by peak / cycle detection on the elbow flexion angle.

This algorithm is deliberately independent of the ML classifier: a repetition is
counted from signal geometry alone, and the classifier only judges its quality.

A Biceps Curl repetition is one cycle  extended -> flexed (peak) -> extended.

1. Peaks in the filtered elbow angle are found with ``scipy.signal.find_peaks``
   using a minimum *prominence* (ignores small accidental movements) and a
   minimum *distance* (prevents counting one peak twice).
2. The lowest angle between neighbouring peaks bounds each cycle, so
   consecutive repetitions cannot overlap. Start / end are then trimmed to the
   movement onset / offset (angle within 10 % of the rise above that valley).
3. A cycle is only counted when the arm has actually come back down
   (descent >= 60 % of the minimum prominence), its duration lies in the
   configured range and it does not span a long data gap.
4. In ``live`` mode a repetition must finish ``edge_guard_s`` before the end of
   the available data, so a rep that is still being lowered is not counted early.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.signal import find_peaks

from physioband_ml.config import PipelineConfig

ONSET_FRACTION = 0.1


@dataclass
class Repetition:
    number: int
    start_idx: int
    peak_idx: int
    end_idx: int
    start_time_s: float
    peak_time_s: float
    end_time_s: float
    rom_deg: float

    @property
    def duration_s(self) -> float:
        return self.end_time_s - self.start_time_s

    def to_dict(self) -> dict:
        data = asdict(self)
        data["duration_s"] = round(self.duration_s, 3)
        return data


def detect_repetitions(
    angle: np.ndarray,
    sample_rate_hz: float,
    cfg: PipelineConfig | None = None,
    gap_mask: np.ndarray | None = None,
    live: bool = False,
) -> list[Repetition]:
    cfg = cfg or PipelineConfig()
    angle = np.asarray(angle, dtype=float)
    n = len(angle)
    if n < 3:
        return []

    distance = max(1, int(cfg.min_peak_distance_s * sample_rate_hz))
    peaks, _ = find_peaks(angle, prominence=cfg.min_rep_prominence_deg, distance=distance)
    if len(peaks) == 0:
        return []

    min_descent = cfg.min_rep_prominence_deg * 0.6
    edge_limit = n - 1 - int(cfg.edge_guard_s * sample_rate_hz) if live else n - 1
    reps: list[Repetition] = []

    for i, peak in enumerate(peaks):
        left_bound = peaks[i - 1] if i > 0 else 0
        right_bound = peaks[i + 1] if i + 1 < len(peaks) else n - 1
        valley_l = left_bound + int(np.argmin(angle[left_bound : peak + 1]))
        valley_r = peak + int(np.argmin(angle[peak : right_bound + 1]))

        rise = angle[peak] - angle[valley_l]
        descent = angle[peak] - angle[valley_r]
        if rise < cfg.min_rep_prominence_deg or descent < min_descent:
            continue  # not a complete cycle (e.g. still lowering the last rep)

        # Trim rest periods: the rep starts when the angle leaves the bottom
        # (10 % of the rise) and ends when it returns there.
        start_thr = angle[valley_l] + ONSET_FRACTION * rise
        end_thr = angle[valley_r] + ONSET_FRACTION * descent
        below_l = np.flatnonzero(angle[valley_l : peak + 1] <= start_thr)
        start = valley_l + int(below_l[-1]) if len(below_l) else valley_l
        below_r = np.flatnonzero(angle[peak : valley_r + 1] <= end_thr)
        end = peak + int(below_r[0]) if len(below_r) else valley_r
        if end > edge_limit:
            continue

        duration = (end - start) / sample_rate_hz
        if not (cfg.min_rep_duration_s <= duration <= cfg.max_rep_duration_s):
            continue
        if gap_mask is not None and gap_mask[start : end + 1].any():
            continue

        reps.append(
            Repetition(
                number=len(reps) + 1,
                start_idx=int(start),
                peak_idx=int(peak),
                end_idx=int(end),
                start_time_s=start / sample_rate_hz,
                peak_time_s=peak / sample_rate_hz,
                end_time_s=end / sample_rate_hz,
                rom_deg=float(angle[peak] - min(angle[valley_l], angle[valley_r])),
            )
        )
    return reps
