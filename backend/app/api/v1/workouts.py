from typing import Literal

from fastapi import APIRouter, Query, status

from app.api.deps import DB, ML, AppSettings, CurrentUser
from app.schemas.analysis import AnalysisResult
from app.schemas.common import Page
from app.schemas.sensor import SensorBatch
from app.schemas.workout import (
    SensorBatchResponse,
    WorkoutComplete,
    WorkoutDetail,
    WorkoutSessionOut,
    WorkoutStart,
)
from app.services.workout_service import WorkoutService

router = APIRouter(prefix="/workouts", tags=["Workout Sessions"])


@router.post("/start", response_model=WorkoutSessionOut, status_code=status.HTTP_201_CREATED)
async def start_workout(data: WorkoutStart, user: CurrentUser, db: DB, ml: ML, settings: AppSettings):
    return await WorkoutService(db, ml, settings).start(user["id"], data)


@router.post("/{session_id}/sensor-data", response_model=SensorBatchResponse)
async def upload_sensor_data(
    session_id: str, batch: SensorBatch, user: CurrentUser, db: DB, ml: ML, settings: AppSettings
):
    """Store a batch of BLE samples and (optionally) return live repetition analysis."""
    return await WorkoutService(db, ml, settings).ingest(user["id"], session_id, batch)


@router.post("/{session_id}/analyze", response_model=AnalysisResult)
async def analyze_workout(session_id: str, user: CurrentUser, db: DB, ml: ML, settings: AppSettings):
    """Run the full analysis on all data received so far (does not close the session)."""
    return await WorkoutService(db, ml, settings).analyze(user["id"], session_id)


@router.post("/{session_id}/complete", response_model=WorkoutDetail)
async def complete_workout(
    session_id: str, user: CurrentUser, db: DB, ml: ML, settings: AppSettings, data: WorkoutComplete | None = None
):
    reason = data.end_reason if data else "user_completed"
    return await WorkoutService(db, ml, settings).complete(user["id"], session_id, reason)


@router.get("", response_model=Page[WorkoutSessionOut])
async def list_workouts(
    user: CurrentUser,
    db: DB,
    ml: ML,
    settings: AppSettings,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    exercise_id: str | None = None,
    status: Literal["active", "completed", "interrupted"] | None = None,
):
    return await WorkoutService(db, ml, settings).list(user["id"], page, page_size, exercise_id, status)


@router.get("/{session_id}", response_model=WorkoutDetail)
async def get_workout(session_id: str, user: CurrentUser, db: DB, ml: ML, settings: AppSettings):
    return await WorkoutService(db, ml, settings).detail(user["id"], session_id)
