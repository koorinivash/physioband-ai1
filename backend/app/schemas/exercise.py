from __future__ import annotations

from app.schemas.common import APIModel


class ExerciseOut(APIModel):
    id: str
    name: str
    description: str
    target_muscles: list[str]
    supported_movement_types: list[str]
    is_active: bool
    order: int = 0
