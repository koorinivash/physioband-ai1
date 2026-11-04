"""Shapes of the documents stored in MongoDB (database ``physioband_ai``).

These TypedDicts document the persisted structure; the API request / response
contracts live in ``app.schemas``. See docs/DATABASE_SCHEMA.md for indexes.
"""
from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from bson import ObjectId


class UserDocument(TypedDict):
    _id: ObjectId
    name: str
    email: str               # unique, lower-case
    password_hash: str       # bcrypt
    profile: dict            # age, gender, height_cm, weight_kg, dominant_arm, training_arm
    created_at: datetime
    updated_at: datetime


class DeviceDocument(TypedDict):
    _id: ObjectId
    user_id: str
    device_id: str           # e.g. "PB-3C61A2F0" (from the ESP32 MAC address)
    device_name: str         # BLE advertised name, e.g. "PhysioBand-A2F0"
    firmware_version: str
    protocol_version: int
    ble_address: str | None
    sample_rate_hz: int | None
    registered_at: datetime
    last_connected_at: datetime


class ExerciseDocument(TypedDict):
    _id: str                 # slug, e.g. "biceps_curl"
    name: str
    description: str
    target_muscles: list[str]
    supported_movement_types: list[str]
    is_active: bool          # only True when recognition + quality assessment are implemented
    order: int


class WorkoutSessionDocument(TypedDict):
    _id: ObjectId
    user_id: str
    device_id: str | None
    exercise_id: str
    exercise_name: str
    status: str              # active | completed | interrupted
    start_time: datetime
    end_time: datetime | None
    duration_s: float | None
    total_reps: int
    correct_reps: int
    incorrect_reps: int
    incomplete_reps: int
    too_fast_reps: int
    irregular_reps: int
    quality_score: float | None
    avg_tension_n: float | None
    peak_tension_n: float | None
    sample_count: int
    batch_count: int
    end_reason: str | None
    suggestions: list[str]
    classification_available: bool
    model_dataset_type: str | None
    last_data_at: datetime | None


class SensorRecordDocument(TypedDict):
    """One document per uploaded batch; arrays are index-aligned per sample."""

    _id: ObjectId
    session_id: str
    user_id: str
    batch_seq: int           # unique per session -> idempotent uploads
    device_id: str | None
    protocol_version: int
    sample_count: int
    start_timestamp_ms: int
    end_timestamp_ms: int
    timestamp_ms: list[int]
    upper_arm_accel: list[list[float | None]]   # [ax, ay, az] in g
    upper_arm_gyro: list[list[float | None]]    # [gx, gy, gz] in deg/s
    forearm_accel: list[list[float | None]]
    forearm_gyro: list[list[float | None]]
    force_n: list[float | None]
    status: list[int]
    received_at: datetime


class WorkoutFeedbackDocument(TypedDict):
    _id: ObjectId
    session_id: str
    repetition_number: int
    classification: str      # correct | incomplete | too_fast | irregular | unclassified
    label_display: str
    confidence: float | None
    message: str
    duration_s: float
    rom_deg: float
    avg_force_n: float
    device_start_ms: float
    device_end_ms: float
    timestamp: datetime
