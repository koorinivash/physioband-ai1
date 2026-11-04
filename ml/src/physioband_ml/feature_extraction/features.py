"""Per-repetition feature extraction.

Features are grouped as:
  * timing      - duration, lifting (concentric) and lowering (eccentric) time
  * range       - elbow range of motion, start / peak angles
  * speed       - elbow angular velocity statistics
  * smoothness  - dimensionless normalised jerk and velocity reversals
  * upper arm   - swing range and rotation rate (should stay small)
  * IMU stats   - accelerometer / gyroscope magnitude statistics per sensor
  * tension     - resistance-band force level and consistency

``FEATURE_NAMES`` fixes the column order. The trained model stores this list and
the predictor refuses to run if the order differs.
"""
from __future__ import annotations

import numpy as np

from physioband_ml.repetition_counting.counter import Repetition
from physioband_ml.segmentation.processing import ProcessedSignals

FEATURE_NAMES: list[str] = [
    "duration_s",
    "concentric_s",
    "eccentric_s",
    "tempo_ratio",
    "rom_deg",
    "start_angle_deg",
    "peak_angle_deg",
    "mean_abs_velocity_dps",
    "peak_velocity_dps",
    "velocity_std_dps",
    "concentric_mean_velocity_dps",
    "eccentric_mean_velocity_dps",
    "velocity_reversals",
    "normalized_jerk",
    "ua_swing_range_deg",
    "ua_gyro_mag_mean",
    "ua_gyro_mag_max",
    "ua_acc_mag_std",
    "fa_gyro_mag_mean",
    "fa_gyro_mag_max",
    "fa_acc_mag_mean",
    "fa_acc_mag_std",
    "fa_acc_mag_max",
    "fa_acc_mag_min",
    "force_mean_n",
    "force_max_n",
    "force_min_n",
    "force_std_n",
    "force_cv",
    "force_range_n",
    "force_rate_std",
]


def _count_reversals(velocity: np.ndarray, threshold: float) -> int:
    """Count sign changes of velocity, ignoring values inside +/- threshold."""
    signs = np.sign(np.where(np.abs(velocity) < threshold, 0.0, velocity))
    signs = signs[signs != 0]
    if len(signs) < 2:
        return 0
    return int(np.count_nonzero(np.diff(signs)))


def _normalized_jerk(angle: np.ndarray, fs: float, duration: float, rom: float) -> float:
    """Dimensionless jerk (Hogan & Sternad). Smooth minimum-jerk motion ~ 7-10; jerky motion is larger."""
    if len(angle) < 5 or rom <= 1e-6 or duration <= 0:
        return 0.0
    dt = 1.0 / fs
    jerk = np.gradient(np.gradient(np.gradient(angle, dt), dt), dt)
    integral = np.sum(jerk**2) * dt
    return float(np.sqrt(0.5 * integral * duration**5 / rom**2))


def extract_rep_features(sig: ProcessedSignals, rep: Repetition) -> dict[str, float]:
    fs = sig.sample_rate_hz
    s, p, e = rep.start_idx, rep.peak_idx, rep.end_idx
    sl = slice(s, e + 1)

    angle = sig.elbow_angle[sl]
    vel = sig.elbow_velocity[sl]
    up_vel = sig.elbow_velocity[s : p + 1]
    down_vel = sig.elbow_velocity[p : e + 1]

    duration = max((e - s) / fs, 1.0 / fs)
    concentric = max((p - s) / fs, 1.0 / fs)
    eccentric = max((e - p) / fs, 1.0 / fs)
    rom = float(angle.max() - angle.min())

    ua_gyro = np.linalg.norm(sig.ua[sl, 3:6], axis=1)
    ua_acc = np.linalg.norm(sig.ua[sl, 0:3], axis=1)
    fa_gyro = np.linalg.norm(sig.fa[sl, 3:6], axis=1)
    fa_acc = np.linalg.norm(sig.fa[sl, 0:3], axis=1)
    force = sig.force[sl]
    force_mean = float(force.mean())

    features = {
        "duration_s": duration,
        "concentric_s": concentric,
        "eccentric_s": eccentric,
        "tempo_ratio": eccentric / concentric,
        "rom_deg": rom,
        "start_angle_deg": float(angle[0]),
        "peak_angle_deg": float(angle.max()),
        "mean_abs_velocity_dps": float(np.mean(np.abs(vel))),
        "peak_velocity_dps": float(np.max(np.abs(vel))),
        "velocity_std_dps": float(np.std(vel)),
        "concentric_mean_velocity_dps": float(np.mean(up_vel)),
        "eccentric_mean_velocity_dps": float(np.mean(-down_vel)),
        "velocity_reversals": float(_count_reversals(vel, threshold=10.0)),
        "normalized_jerk": _normalized_jerk(angle, fs, duration, rom),
        "ua_swing_range_deg": float(np.ptp(sig.ua_swing[sl])),
        "ua_gyro_mag_mean": float(ua_gyro.mean()),
        "ua_gyro_mag_max": float(ua_gyro.max()),
        "ua_acc_mag_std": float(ua_acc.std()),
        "fa_gyro_mag_mean": float(fa_gyro.mean()),
        "fa_gyro_mag_max": float(fa_gyro.max()),
        "fa_acc_mag_mean": float(fa_acc.mean()),
        "fa_acc_mag_std": float(fa_acc.std()),
        "fa_acc_mag_max": float(fa_acc.max()),
        "fa_acc_mag_min": float(fa_acc.min()),
        "force_mean_n": force_mean,
        "force_max_n": float(force.max()),
        "force_min_n": float(force.min()),
        "force_std_n": float(force.std()),
        "force_cv": float(force.std() / abs(force_mean)) if abs(force_mean) > 1e-3 else 0.0,
        "force_range_n": float(np.ptp(force)),
        "force_rate_std": float(np.std(np.gradient(force) * fs)),
    }
    return {name: float(features[name]) for name in FEATURE_NAMES}


def features_to_matrix(rows: list[dict[str, float]]) -> np.ndarray:
    return np.array([[row[name] for name in FEATURE_NAMES] for row in rows], dtype=float)
