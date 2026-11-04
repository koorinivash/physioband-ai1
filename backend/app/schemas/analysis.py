from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel
from app.schemas.sensor import SensorSample


class ModelStatus(APIModel):
    available: bool
    algorithm: str | None = None
    model_version: str | None = None
    dataset_type: str | None = Field(default=None, description="synthetic | collected")
    validated: bool = False
    status_note: str


class ModelInfo(ModelStatus):
    trained_at: str | None = None
    classes: list[str] = []
    feature_count: int | None = None
    training_samples: int | None = None
    test_samples: int | None = None
    metrics: dict | None = None
    exercise_ids: list[str] = []
    load_error: str | None = None


class RepetitionOut(APIModel):
    number: int
    start_timestamp_ms: float
    end_timestamp_ms: float
    duration_s: float
    rom_deg: float
    avg_force_n: float
    peak_force_n: float
    label: str
    label_display: str
    confidence: float | None = None
    probabilities: dict[str, float] | None = None
    feedback: str
    features: dict[str, float] | None = None


class LiveStatusOut(APIModel):
    movement_phase: Literal["lifting", "lowering", "holding", "resting"]
    upper_arm_status: Literal["stable", "moving", "excessive_swing"]
    forearm_status: Literal["active", "still"]
    current_angle_deg: float
    current_force_n: float
    upper_arm_swing_deg: float


class AnalysisResult(APIModel):
    exercise_id: str
    mode: Literal["live", "final", "standalone"]
    analyzed_at: datetime
    sample_count: int
    duration_s: float
    total_reps: int
    correct_reps: int
    incorrect_reps: int
    incomplete_reps: int
    too_fast_reps: int
    irregular_reps: int
    unclassified_reps: int
    quality_score: float | None
    avg_tension_n: float | None
    peak_tension_n: float | None
    classification_available: bool
    reps: list[RepetitionOut]
    new_reps: list[RepetitionOut] = Field(default_factory=list, description="Reps first reported in this response")
    live: LiveStatusOut | None = None
    suggestions: list[str]
    processing_notes: list[str] = []
    validation: dict
    model: ModelStatus


class PredictRequest(APIModel):
    exercise_id: str = "biceps_curl"
    samples: list[SensorSample] = Field(min_length=10)
    include_features: bool = False
