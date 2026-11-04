from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import USERS
from app.repositories.base import serialize, to_object_id, utcnow


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db[USERS]

    async def create(self, name: str, email: str, password_hash: str) -> dict:
        doc = {
            "name": name,
            "email": email.lower(),
            "password_hash": password_hash,
            "profile": {},
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        result = await self.col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return serialize(doc)

    async def get_by_email(self, email: str) -> dict | None:
        return serialize(await self.col.find_one({"email": email.lower()}))

    async def get_by_id(self, user_id: str) -> dict | None:
        return serialize(await self.col.find_one({"_id": to_object_id(user_id, "user")}))

    async def update(self, user_id: str, fields: dict) -> dict | None:
        fields["updated_at"] = utcnow()
        await self.col.update_one({"_id": to_object_id(user_id, "user")}, {"$set": fields})
        return await self.get_by_id(user_id)
