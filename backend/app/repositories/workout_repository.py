from __future__ import annotations

from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import WORKOUT_SESSIONS
from app.repositories.base import serialize, to_object_id, utcnow


class WorkoutRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db[WORKOUT_SESSIONS]

    async def create(self, user_id: str, exercise: dict, device_id: str | None) -> dict:
        doc = {
            "user_id": user_id,
            "device_id": device_id,
            "exercise_id": exercise["id"],
            "exercise_name": exercise["name"],
            "status": "active",
            "start_time": utcnow(),
            "end_time": None,
            "duration_s": None,
            "total_reps": 0,
            "correct_reps": 0,
            "incorrect_reps": 0,
            "incomplete_reps": 0,
            "too_fast_reps": 0,
            "irregular_reps": 0,
            "quality_score": None,
            "avg_tension_n": None,
            "peak_tension_n": None,
            "sample_count": 0,
            "batch_count": 0,
            "end_reason": None,
            "suggestions": [],
            "classification_available": False,
            "model_dataset_type": None,
            "last_data_at": None,
        }
        result = await self.col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return serialize(doc)

    async def get(self, user_id: str, session_id: str) -> dict | None:
        return serialize(await self.col.find_one({"_id": to_object_id(session_id, "session"), "user_id": user_id}))

    async def update(self, session_id: str, fields: dict) -> None:
        await self.col.update_one({"_id": to_object_id(session_id, "session")}, {"$set": fields})

    async def add_samples(self, session_id: str, count: int) -> None:
        await self.col.update_one(
            {"_id": to_object_id(session_id, "session")},
            {"$inc": {"sample_count": count, "batch_count": 1}, "$set": {"last_data_at": utcnow()}},
        )

    async def active_for_user(self, user_id: str) -> list[dict]:
        return [serialize(d) async for d in self.col.find({"user_id": user_id, "status": "active"})]

    async def page(self, user_id: str, page: int, page_size: int, exercise_id: str | None, status: str | None):
        query: dict = {"user_id": user_id}
        if exercise_id:
            query["exercise_id"] = exercise_id
        if status:
            query["status"] = status
        total = await self.col.count_documents(query)
        cursor = self.col.find(query).sort("start_time", -1).skip((page - 1) * page_size).limit(page_size)
        return [serialize(d) async for d in cursor], total

    async def finished_since(self, user_id: str, since: datetime | None) -> list[dict]:
        query: dict = {"user_id": user_id, "status": {"$in": ["completed", "interrupted"]}}
        if since is not None:
            query["start_time"] = {"$gte": since}
        return [serialize(d) async for d in self.col.find(query).sort("start_time", 1)]
