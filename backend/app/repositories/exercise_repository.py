from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import EXERCISES
from app.repositories.base import serialize


class ExerciseRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db[EXERCISES]

    async def list(self, active_only: bool = False) -> list[dict]:
        query = {"is_active": True} if active_only else {}
        return [serialize(d) async for d in self.col.find(query).sort("order", 1)]

    async def get(self, exercise_id: str) -> dict | None:
        return serialize(await self.col.find_one({"_id": exercise_id}))
