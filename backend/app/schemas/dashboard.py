from __future__ import annotations

from app.schemas.analysis import ModelStatus
from app.schemas.common import APIModel
from app.schemas.workout import WorkoutSessionOut


class PeriodStats(APIModel):
    sessions: int
    total_reps: int
    correct_reps: int
    incorrect_reps: int
    quality_score: float | None
    active_minutes: float
    avg_tension_n: float | None


class DashboardSummary(APIModel):
    today: PeriodStats
    all_time: PeriodStats
    recent_sessions: list[WorkoutSessionOut]
    active_session_id: str | None
    model: ModelStatus


class PerformancePoint(APIModel):
    date: str
    sessions: int
    total_reps: int
    correct_reps: int
    quality_score: float | None
    avg_tension_n: float | None


class PerformanceResponse(APIModel):
    days: int
    points: list[PerformancePoint]
    quality_trend: float | None = None
    best_quality: float | None = None
    total_reps: int = 0
