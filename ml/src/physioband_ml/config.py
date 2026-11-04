"""Shared constants and tunable configuration for the PhysioBand AI ML pipeline.

Every value used by BOTH training and inference lives here so the two paths can
never drift apart. Thresholds are engineering defaults for a Biceps Curl and are
expected to be re-tuned once real volunteer data has been collected.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

# ---------------------------------------------------------------------------
# Sensor channel names (must match firmware -> app -> backend -> CSV format)
# ---------------------------------------------------------------------------
UPPER_ARM_CHANNELS = ["ua_ax", "ua_ay", "ua_az", "ua_gx", "ua_gy", "ua_gz"]
FOREARM_CHANNELS = ["fa_ax", "fa_ay", "fa_az", "fa_gx", "fa_gy", "fa_gz"]
FORCE_CHANNEL = "force_n"
TIMESTAMP_COLUMN = "timestamp_ms"
SENSOR_CHANNELS = UPPER_ARM_CHANNELS + FOREARM_CHANNELS + [FORCE_CHANNEL]

# Optional metadata columns in training CSV files
META_COLUMNS = ["participant_id", "session_id", "exercise_id", "label", "is_synthetic"]

# Movement-quality classes supported for the Biceps Curl
LABEL_CORRECT = "correct"
LABEL_INCOMPLETE = "incomplete"
LABEL_TOO_FAST = "too_fast"
LABEL_IRREGULAR = "irregular"
QUALITY_LABELS = [LABEL_CORRECT, LABEL_INCOMPLETE, LABEL_TOO_FAST, LABEL_IRREGULAR]
LABEL_UNCLASSIFIED = "unclassified"

LABEL_DISPLAY = {
    LABEL_CORRECT: "Correct Movement",
    LABEL_INCOMPLETE: "Incomplete Movement",
    LABEL_TOO_FAST: "Excessively Fast Movement",
    LABEL_IRREGULAR: "Irregular Movement",
    LABEL_UNCLASSIFIED: "Not Classified",
}

FEEDBACK_MESSAGES = {
    LABEL_CORRECT: "Good repetition: full range of motion with a controlled tempo.",
    LABEL_INCOMPLETE: "Incomplete range: curl higher and extend the elbow fully at the bottom.",
    LABEL_TOO_FAST: "Too fast: slow down and control both the lifting and lowering phases.",
    LABEL_IRREGULAR: "Irregular movement: keep the motion smooth and the upper arm steady.",
    LABEL_UNCLASSIFIED: "Repetition counted. Quality classification is unavailable.",
}

SUPPORTED_EXERCISES = ["biceps_curl"]

# Physical sanity limits (MPU6050 configured at +/-8 g and +/-1000 deg/s)
ACCEL_LIMIT_G = 8.5
GYRO_LIMIT_DPS = 1050.0
FORCE_MIN_N = -50.0
FORCE_MAX_N = 2000.0


@dataclass
class PipelineConfig:
    """Tunable parameters for preprocessing, segmentation and rep counting."""

    sample_rate_hz: float = 50.0
    max_gap_ms: float = 200.0           # gaps longer than this are not interpolated
    lowpass_cutoff_hz: float = 5.0      # Butterworth low-pass cut-off for noise filtering
    lowpass_order: int = 4
    complementary_alpha: float = 0.98   # gyro weight in the gravity-vector filter

    # Repetition counting on the elbow flexion angle (degrees)
    min_rep_prominence_deg: float = 25.0  # movements smaller than this are ignored
    min_rep_duration_s: float = 0.5
    max_rep_duration_s: float = 10.0
    min_peak_distance_s: float = 0.6     # avoids double counting a single peak
    edge_guard_s: float = 0.6            # live mode: a rep must end this long before the data end

    # Rule thresholds used only for labelling synthetic data and for feedback text
    full_rom_deg: float = 95.0
    fast_rep_duration_s: float = 1.5

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "PipelineConfig":
        if not data:
            return cls()
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)


@dataclass
class CalibrationConfig:
    """Per-device calibration applied before filtering.

    Gyro bias is in deg/s, accelerometer offsets in g, force offset in N.
    The load-cell scale factor itself is applied on the ESP32 (see firmware).
    """

    ua_gyro_bias: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    fa_gyro_bias: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    ua_accel_offset: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    fa_accel_offset: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    force_offset_n: float = 0.0
    force_scale: float = 1.0

    @classmethod
    def from_dict(cls, data: dict | None) -> "CalibrationConfig":
        if not data:
            return cls()
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)
