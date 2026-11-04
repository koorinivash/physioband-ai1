"""Sensor records are stored in BATCHES (one document per upload of ~50-100 samples)
instead of one document per sample. This keeps Atlas writes to ~1 per second during
a workout while still storing every reading in column (array) form."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.database.mongodb import SENSOR_RECORDS
from app.repositories.base import utcnow


class SensorRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db[SENSOR_RECORDS]

    async def insert_batch(self, session_id: str, user_id: str, batch_seq: int, device_id: str | None,
                           protocol_version: int, samples: list[dict]) -> bool:
        """Store a batch. Returns False when this batch_seq was already stored (retry)."""
        doc = {
            "session_id": session_id,
            "user_id": user_id,
            "batch_seq": batch_seq,
            "device_id": device_id,
            "protocol_version": protocol_version,
            "sample_count": len(samples),
            "start_timestamp_ms": samples[0]["timestamp_ms"],
            "end_timestamp_ms": samples[-1]["timestamp_ms"],
            "timestamp_ms": [s["timestamp_ms"] for s in samples],
            "upper_arm_accel": [s["ua"][0:3] for s in samples],
            "upper_arm_gyro": [s["ua"][3:6] for s in samples],
            "forearm_accel": [s["fa"][0:3] for s in samples],
            "forearm_gyro": [s["fa"][3:6] for s in samples],
            "force_n": [s["force_n"] for s in samples],
            "status": [s["status"] for s in samples],
            "received_at": utcnow(),
        }
        try:
            await self.col.insert_one(doc)
            return True
        except DuplicateKeyError:
            return False

    async def load_samples(self, session_id: str) -> list[dict]:
        """Load all samples of a session back into the API sample format, in time order."""
        samples: list[dict] = []
        cursor = self.col.find({"session_id": session_id}).sort("batch_seq", 1)
        async for doc in cursor:
            for i, ts in enumerate(doc["timestamp_ms"]):
                samples.append(
                    {
                        "timestamp_ms": ts,
                        "ua": [*doc["upper_arm_accel"][i], *doc["upper_arm_gyro"][i]],
                        "fa": [*doc["forearm_accel"][i], *doc["forearm_gyro"][i]],
                        "force_n": doc["force_n"][i],
                        "status": doc["status"][i],
                    }
                )
        samples.sort(key=lambda s: s["timestamp_ms"])
        return samples
