from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.analysis import AnalysisResult
from app.schemas.common import APIModel

SessionStatus = Literal["active", "completed", "interrupted"]
EndReason = Literal["user_completed", "device_disconnected", "app_interrupted", "superseded"]


class WorkoutStart(APIModel):
    exercise_id: str = Field(examples=["biceps_curl"])
    device_id: str | None = Field(default=None, max_length=40)


class WorkoutComplete(APIModel):
    end_reason: EndReason = "user_completed"


class WorkoutSessionOut(APIModel):
    id: str
    user_id: str
    device_id: str | None
    exercise_id: str
    exercise_name: str
    status: SessionStatus
    start_time: datetime
    end_time: datetime | None = None
    duration_s: float | None = None
    total_reps: int = 0
    correct_reps: int = 0
    incorrect_reps: int = 0
    incomplete_reps: int = 0
    too_fast_reps: int = 0
    irregular_reps: int = 0
    quality_score: float | None = None
    avg_tension_n: float | None = None
    peak_tension_n: float | None = None
    sample_count: int = 0
    batch_count: int = 0
    end_reason: EndReason | None = None
    suggestions: list[str] = []
    classification_available: bool = False
    model_dataset_type: str | None = None


class FeedbackOut(APIModel):
    repetition_number: int
    classification: str
    label_display: str
    confidence: float | None
    message: str
    duration_s: float
    rom_deg: float
    avg_force_n: float
    timestamp: datetime


class WorkoutDetail(WorkoutSessionOut):
    feedback: list[FeedbackOut] = []


class SensorBatchResponse(APIModel):
    session_id: str
    batch_seq: int
    accepted: bool
    duplicate: bool
    stored_samples: int
    total_samples: int
    analysis: AnalysisResult | None = None
    analysis_error: str | None = None
