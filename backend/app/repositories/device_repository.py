from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.database.mongodb import DEVICES
from app.repositories.base import serialize, utcnow


class DeviceRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db[DEVICES]

    async def upsert(self, user_id: str, data: dict) -> dict:
        now = utcnow()
        doc = await self.col.find_one_and_update(
            {"user_id": user_id, "device_id": data["device_id"]},
            {"$set": {**data, "last_connected_at": now}, "$setOnInsert": {"registered_at": now}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return serialize(doc)

    async def list_for_user(self, user_id: str) -> list[dict]:
        cursor = self.col.find({"user_id": user_id}).sort("last_connected_at", -1)
        return [serialize(d) async for d in cursor]

    async def get(self, user_id: str, device_id: str) -> dict | None:
        return serialize(await self.col.find_one({"user_id": user_id, "device_id": device_id}))

    async def delete(self, user_id: str, device_id: str) -> bool:
        result = await self.col.delete_one({"user_id": user_id, "device_id": device_id})
        return result.deleted_count == 1
