"""Joint-angle estimation from the two MPU6050 sensors.

Each IMU tracks the direction of gravity in its own sensor frame with a
complementary filter: the gyroscope rotates the previous estimate (accurate over
short periods) and the accelerometer slowly pulls it back (no long-term drift).

Mounting assumption (see docs/HARDWARE_SETUP.md): both sensors are strapped with
the same orientation relative to their limb segment, X axis pointing towards the
hand. With the arm hanging straight, both sensors then see gravity in the same
direction, so the angle between the two gravity vectors is the elbow flexion
angle (0 deg = extended, ~140 deg = fully curled).

The upper-arm swing angle is the rotation of the upper-arm gravity vector away
from its starting direction; during a correct curl the upper arm stays still.
"""
from __future__ import annotations

import math

import numpy as np


def track_gravity(accel_g: np.ndarray, gyro_dps: np.ndarray, sample_rate_hz: float, alpha: float) -> np.ndarray:
    """Return unit gravity-direction vectors ``[n, 3]`` in the sensor frame."""
    n = accel_g.shape[0]
    dt = 1.0 / sample_rate_hz
    beta = 1.0 - alpha
    # The filter is recursive, so it cannot be vectorised; plain float arithmetic
    # on Python lists is ~15x faster here than numpy operations on 3-vectors.
    acc = accel_g.tolist()
    om = (np.deg2rad(gyro_dps) * dt).tolist()
    out = [None] * n

    x, y, z = acc[0]
    norm = math.sqrt(x * x + y * y + z * z)
    x, y, z = (x / norm, y / norm, z / norm) if norm > 1e-6 else (1.0, 0.0, 0.0)
    out[0] = (x, y, z)

    for k in range(1, n):
        wx, wy, wz = om[k]
        # A world-fixed vector seen from a rotating frame changes by -omega x v.
        px = x - (wy * z - wz * y)
        py = y - (wz * x - wx * z)
        pz = z - (wx * y - wy * x)
        ax, ay, az = acc[k]
        an = math.sqrt(ax * ax + ay * ay + az * az)
        if 0.5 < an < 1.5:
            # Only trust the accelerometer when it mostly measures gravity.
            px = alpha * px + beta * ax / an
            py = alpha * py + beta * ay / an
            pz = alpha * pz + beta * az / an
        bn = math.sqrt(px * px + py * py + pz * pz)
        if bn > 1e-9:
            x, y, z = px / bn, py / bn, pz / bn
        out[k] = (x, y, z)
    return np.array(out, dtype=float)


def angle_between(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Row-wise angle in degrees between two arrays of unit vectors."""
    dots = np.clip(np.einsum("ij,ij->i", u, v), -1.0, 1.0)
    return np.degrees(np.arccos(dots))


def compute_kinematics(ua: np.ndarray, fa: np.ndarray, sample_rate_hz: float, alpha: float) -> dict[str, np.ndarray]:
    """Compute elbow angle, angular velocity and upper-arm swing.

    ``ua`` / ``fa`` are ``[n, 6]`` arrays: accel xyz (g) followed by gyro xyz (deg/s).
    """
    g_ua = track_gravity(ua[:, 0:3], ua[:, 3:6], sample_rate_hz, alpha)
    g_fa = track_gravity(fa[:, 0:3], fa[:, 3:6], sample_rate_hz, alpha)

    elbow_angle = angle_between(g_ua, g_fa)
    elbow_velocity = np.gradient(elbow_angle) * sample_rate_hz

    ref_len = max(1, min(len(g_ua), int(sample_rate_hz * 0.5)))
    ref = g_ua[:ref_len].mean(axis=0)
    ref /= np.linalg.norm(ref) or 1.0
    ua_swing = angle_between(g_ua, np.repeat(ref[None, :], len(g_ua), axis=0))

    return {
        "elbow_angle": elbow_angle,
        "elbow_velocity": elbow_velocity,
        "ua_swing": ua_swing,
    }
