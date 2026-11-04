from fastapi import APIRouter, Query

from app.api.deps import DB, CurrentUser
from app.core.exceptions import NotFoundError
from app.repositories.exercise_repository import ExerciseRepository
from app.schemas.exercise import ExerciseOut

router = APIRouter(prefix="/exercises", tags=["Exercise Management"])


@router.get("", response_model=list[ExerciseOut])
async def list_exercises(_: CurrentUser, db: DB, active_only: bool = Query(False)):
    """All exercises. Only exercises with ``is_active=true`` have implemented analysis."""
    return await ExerciseRepository(db).list(active_only)


@router.get("/{exercise_id}", response_model=ExerciseOut)
async def get_exercise(exercise_id: str, _: CurrentUser, db: DB):
    exercise = await ExerciseRepository(db).get(exercise_id)
    if not exercise:
        raise NotFoundError("Exercise not found", code="EXERCISE_NOT_FOUND")
    return exercise
