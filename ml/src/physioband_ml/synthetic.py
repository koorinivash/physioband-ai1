"""SYNTHETIC biceps-curl sensor data generator.

!!! This data is simulated. It exists ONLY to test the software pipeline end to end
!!! before real volunteer recordings are available. Models trained on it are demo
!!! models and their metrics say nothing about real-world exercise assessment.

Simple physical model (both IMUs mounted X-axis along the limb, curl about Y):
  * upper-arm inclination psi(t): ~0 for good form, swings for "irregular" reps
  * elbow flexion theta(t): minimum-jerk lift / lower profile per repetition
  * forearm inclination = psi + theta
  * accelerometer = gravity reaction in the sensor frame + tangential / centripetal
    acceleration of the forearm sensor + noise
  * gyroscope_y = -d(inclination)/dt  (sign consistent with the gravity tracker)
  * band force = base tension + stiffness * stretch(theta) + noise
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from physioband_ml.config import (
    FOREARM_CHANNELS,
    LABEL_CORRECT,
    LABEL_INCOMPLETE,
    LABEL_IRREGULAR,
    LABEL_TOO_FAST,
    TIMESTAMP_COLUMN,
    UPPER_ARM_CHANNELS,
)

G = 9.80665
FOREARM_SENSOR_RADIUS_M = 0.15


@dataclass
class ParticipantProfile:
    participant_id: str
    rom_scale: float
    tempo_scale: float
    base_tension_n: float
    band_stiffness_n: float
    accel_noise_g: float
    gyro_noise_dps: float
    gyro_bias_dps: float


def random_profile(participant_id: str, rng: np.random.Generator) -> ParticipantProfile:
    return ParticipantProfile(
        participant_id=participant_id,
        rom_scale=rng.uniform(0.9, 1.08),
        tempo_scale=rng.uniform(0.85, 1.2),
        base_tension_n=rng.uniform(8, 20),
        band_stiffness_n=rng.uniform(35, 90),
        accel_noise_g=rng.uniform(0.006, 0.015),
        gyro_noise_dps=rng.uniform(0.4, 1.2),
        gyro_bias_dps=rng.uniform(-1.5, 1.5),
    )


def _min_jerk(n: int) -> np.ndarray:
    tau = np.linspace(0.0, 1.0, max(n, 2))
    return 10 * tau**3 - 15 * tau**4 + 6 * tau**5


def _rep_parameters(label: str, prof: ParticipantProfile, rng: np.random.Generator) -> dict:
    if label == LABEL_CORRECT:
        rom, up, down = rng.uniform(110, 140), rng.uniform(1.0, 1.7), rng.uniform(1.2, 2.1)
    elif label == LABEL_INCOMPLETE:
        rom, up, down = rng.uniform(35, 72), rng.uniform(0.8, 1.5), rng.uniform(0.9, 1.7)
    elif label == LABEL_TOO_FAST:
        rom, up, down = rng.uniform(100, 135), rng.uniform(0.3, 0.5), rng.uniform(0.3, 0.55)
    elif label == LABEL_IRREGULAR:
        rom, up, down = rng.uniform(95, 135), rng.uniform(1.0, 1.8), rng.uniform(1.1, 2.0)
    else:
        raise ValueError(f"Unknown label {label}")
    tempo = prof.tempo_scale if label != LABEL_TOO_FAST else 1.0
    return {
        "rom": rom * (prof.rom_scale if label != LABEL_INCOMPLETE else 1.0),
        "up": up * tempo,
        "down": down * tempo,
        "hold": rng.uniform(0.0, 0.3),
        "rest": rng.uniform(0.4, 1.0),
        "start": rng.uniform(4, 14),
    }


def generate_set(
    label: str,
    n_reps: int,
    prof: ParticipantProfile,
    session_id: str,
    rng: np.random.Generator,
    fs: float = 50.0,
    drop_rate: float = 0.004,
) -> pd.DataFrame:
    """Generate one recorded set of ``n_reps`` repetitions of the given quality label."""
    theta_parts = [np.full(int(fs * rng.uniform(1.5, 2.5)), rng.uniform(4, 12))]
    psi_parts = [np.zeros(len(theta_parts[0]))]

    for _ in range(n_reps):
        p = _rep_parameters(label, prof, rng)
        base = theta_parts[-1][-1]
        n_up, n_hold, n_down, n_rest = (max(2, int(fs * p[k])) for k in ("up", "hold", "down", "rest"))
        peak = base + p["rom"]
        up = base + (peak - base) * _min_jerk(n_up)
        hold = np.full(n_hold, peak)
        end = p["start"]
        down = peak + (end - peak) * _min_jerk(n_down)
        rest = np.full(n_rest, end)
        rep_theta = np.concatenate([up, hold, down])
        rep_psi = np.zeros(len(rep_theta)) + rng.normal(0, 0.5)

        if label == LABEL_IRREGULAR:
            t = np.arange(len(rep_theta)) / fs
            mode = rng.integers(0, 3)
            if mode in (0, 2):  # jerky / shaky motion
                freq, amp = rng.uniform(1.8, 3.5), rng.uniform(6, 12)
                env = np.sin(np.pi * np.linspace(0, 1, len(rep_theta)))
                rep_theta = rep_theta + amp * env * np.sin(2 * np.pi * freq * t)
            if mode in (1, 2):  # swinging the upper arm to cheat the lift
                swing = rng.uniform(14, 30)
                rep_psi = rep_psi + swing * np.sin(np.pi * np.linspace(0, 1, len(rep_theta))) ** 2
            if mode == 1:  # stop-and-go: a pause in the middle of the lift
                pause = np.full(int(fs * rng.uniform(0.3, 0.6)), rep_theta[n_up // 2])
                idx = n_up // 2
                rep_theta = np.concatenate([rep_theta[:idx], pause, rep_theta[idx:]])
                rep_psi = np.concatenate([rep_psi[:idx], np.full(len(pause), rep_psi[idx]), rep_psi[idx:]])

        theta_parts += [rep_theta, rest]
        psi_parts += [rep_psi, np.full(n_rest, rep_psi[-1] * 0.2)]

    tail = int(fs * 1.5)
    theta_parts.append(np.full(tail, theta_parts[-1][-1]))
    psi_parts.append(np.zeros(tail))
    theta = np.concatenate(theta_parts)
    psi = np.concatenate(psi_parts)
    # Smooth joins between segments.
    kernel = np.ones(5) / 5
    theta = np.convolve(np.pad(theta, 2, mode="edge"), kernel, mode="valid")
    psi = np.convolve(np.pad(psi, 2, mode="edge"), kernel, mode="valid")
    return _render(theta, psi, label, prof, session_id, rng, fs, drop_rate)


def _render(theta, psi, label, prof, session_id, rng, fs, drop_rate) -> pd.DataFrame:
    n = len(theta)
    dt = 1.0 / fs
    ua_incl = np.deg2rad(psi)
    fa_incl = np.deg2rad(psi + theta)

    def accel(incl: np.ndarray) -> np.ndarray:
        return np.column_stack([-np.cos(incl), np.zeros_like(incl), np.sin(incl)])

    ua_acc = accel(ua_incl)
    fa_acc = accel(fa_incl)
    omega = np.gradient(fa_incl, dt)
    alpha = np.gradient(omega, dt)
    fa_acc[:, 2] += FOREARM_SENSOR_RADIUS_M * alpha / G
    fa_acc[:, 0] += FOREARM_SENSOR_RADIUS_M * omega**2 / G

    ua_gyro = np.zeros((n, 3))
    fa_gyro = np.zeros((n, 3))
    ua_gyro[:, 1] = -np.degrees(np.gradient(ua_incl, dt))
    fa_gyro[:, 1] = -np.degrees(np.gradient(fa_incl, dt))

    ua_acc += rng.normal(0, prof.accel_noise_g, (n, 3))
    fa_acc += rng.normal(0, prof.accel_noise_g, (n, 3))
    ua_gyro += rng.normal(0, prof.gyro_noise_dps, (n, 3)) + prof.gyro_bias_dps
    fa_gyro += rng.normal(0, prof.gyro_noise_dps, (n, 3)) - prof.gyro_bias_dps

    stretch = np.clip(theta, 0, None) / 150.0
    force = prof.base_tension_n + prof.band_stiffness_n * stretch + rng.normal(0, 0.35, n)
    if label == LABEL_IRREGULAR:
        force += rng.normal(0, 1.5, n)

    start_ms = float(rng.integers(10_000, 500_000))
    ts = start_ms + np.arange(n) * dt * 1000.0 + rng.normal(0, 1.0, n)
    ts = np.maximum.accumulate(np.round(ts))

    df = pd.DataFrame(np.column_stack([ua_acc, ua_gyro]), columns=UPPER_ARM_CHANNELS)
    df[FOREARM_CHANNELS] = np.column_stack([fa_acc, fa_gyro])
    df["force_n"] = force
    df.insert(0, TIMESTAMP_COLUMN, ts.astype(np.int64))
    df.insert(0, "is_synthetic", True)
    df.insert(0, "label", label)
    df.insert(0, "exercise_id", "biceps_curl")
    df.insert(0, "session_id", session_id)
    df.insert(0, "participant_id", prof.participant_id)

    keep = rng.random(n) >= drop_rate  # simulate occasional BLE packet loss
    keep[:5] = keep[-5:] = True
    return df.loc[keep].round(4).reset_index(drop=True)


def generate_dataset(
    n_participants: int = 10,
    reps_per_set: int = 10,
    sets_per_label: int = 1,
    seed: int = 7,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frames = []
    for p in range(n_participants):
        prof = random_profile(f"SYN-P{p + 1:02d}", rng)
        for label in (LABEL_CORRECT, LABEL_INCOMPLETE, LABEL_TOO_FAST, LABEL_IRREGULAR):
            for s in range(sets_per_label):
                session_id = f"{prof.participant_id}-{label}-{s + 1}"
                frames.append(generate_set(label, reps_per_set, prof, session_id, rng))
    return pd.concat(frames, ignore_index=True)


def generate_mixed_stream(seed: int = 3, reps: tuple[str, ...] | None = None) -> pd.DataFrame:
    """A single synthetic workout mixing quality labels, used by tests and the device simulator."""
    rng = np.random.default_rng(seed)
    prof = random_profile("SYN-DEMO", rng)
    reps = reps or (LABEL_CORRECT,) * 4 + (LABEL_INCOMPLETE, LABEL_CORRECT, LABEL_TOO_FAST, LABEL_IRREGULAR)
    parts = []
    offset = 0.0
    for i, label in enumerate(reps):
        part = generate_set(label, 1, prof, "SYN-DEMO-STREAM", rng, drop_rate=0.0)
        part[TIMESTAMP_COLUMN] = part[TIMESTAMP_COLUMN] - part[TIMESTAMP_COLUMN].iloc[0] + offset
        offset = float(part[TIMESTAMP_COLUMN].iloc[-1]) + 20.0
        parts.append(part)
    return pd.concat(parts, ignore_index=True)
