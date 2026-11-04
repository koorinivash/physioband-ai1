from __future__ import annotations

from datetime import timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import WORKOUT_FEEDBACK
from app.repositories.base import serialize, utcnow


class FeedbackRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db[WORKOUT_FEEDBACK]

    async def known_rep_numbers(self, session_id: str) -> set[int]:
        cursor = self.col.find({"session_id": session_id}, {"repetition_number": 1})
        return {d["repetition_number"] async for d in cursor}

    async def upsert_reps(self, session_id: str, reps: list[dict]) -> None:
        # A handful of reps per call, so one upsert each keeps this simple and portable.
        for rep in reps:
            await self.col.update_one(
                {"session_id": session_id, "repetition_number": rep["number"]},
                {
                    "$set": {
                        "classification": rep["label"],
                        "label_display": rep["label_display"],
                        "confidence": rep["confidence"],
                        "message": rep["feedback"],
                        "duration_s": rep["duration_s"],
                        "rom_deg": rep["rom_deg"],
                        "avg_force_n": rep["avg_force_n"],
                        "device_start_ms": rep["start_timestamp_ms"],
                        "device_end_ms": rep["end_timestamp_ms"],
                        "timestamp": utcnow(),
                    }
                },
                upsert=True,
            )

    async def delete_from(self, session_id: str, first_number: int) -> None:
        """Remove reps that disappeared after the final re-analysis."""
        await self.col.delete_many({"session_id": session_id, "repetition_number": {"$gte": first_number}})

    async def list_for_session(self, session_id: str) -> list[dict]:
        cursor = self.col.find({"session_id": session_id}).sort("repetition_number", 1)
        out = []
        async for doc in cursor:
            doc = serialize(doc)
            if doc["timestamp"].tzinfo is None:
                doc["timestamp"] = doc["timestamp"].replace(tzinfo=timezone.utc)
            out.append(doc)
        return out
