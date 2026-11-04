"""MongoDB Atlas connection management, indexes and seed data."""
from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import PyMongoError

from app.core.config import Settings

log = logging.getLogger(__name__)

USERS = "users"
DEVICES = "devices"
EXERCISES = "exercises"
WORKOUT_SESSIONS = "workout_sessions"
SENSOR_RECORDS = "sensor_records"
WORKOUT_FEEDBACK = "workout_feedback"

INDEXES: dict[str, list[IndexModel]] = {
    USERS: [IndexModel([("email", ASCENDING)], unique=True, name="uniq_email")],
    DEVICES: [
        IndexModel([("user_id", ASCENDING), ("device_id", ASCENDING)], unique=True, name="uniq_user_device"),
    ],
    WORKOUT_SESSIONS: [
        IndexModel([("user_id", ASCENDING), ("start_time", DESCENDING)], name="user_history"),
        IndexModel([("user_id", ASCENDING), ("status", ASCENDING)], name="user_status"),
    ],
    SENSOR_RECORDS: [
        # Unique batch sequence makes uploads idempotent: a retried batch is not stored twice.
        IndexModel([("session_id", ASCENDING), ("batch_seq", ASCENDING)], unique=True, name="uniq_session_batch"),
    ],
    WORKOUT_FEEDBACK: [
        IndexModel([("session_id", ASCENDING), ("repetition_number", ASCENDING)], unique=True, name="uniq_session_rep"),
    ],
}

# Only Biceps Curl is operational. The others are listed so the app can show them as
# "coming soon"; they are marked inactive until recognition and quality assessment exist.
EXERCISE_SEED = [
    {
        "_id": "biceps_curl",
        "name": "Biceps Curl",
        "description": "Standing resistance-band elbow flexion. Keep the upper arm still and curl through the full range.",
        "target_muscles": ["Biceps brachii", "Brachialis"],
        "supported_movement_types": ["correct", "incomplete", "too_fast", "irregular"],
        "is_active": True,
        "order": 1,
    },
    {
        "_id": "shoulder_press",
        "name": "Shoulder Press",
        "description": "Overhead pressing movement with the resistance band.",
        "target_muscles": ["Deltoids", "Triceps"],
        "supported_movement_types": [],
        "is_active": False,
        "order": 2,
    },
    {
        "_id": "chest_press",
        "name": "Chest Press",
        "description": "Horizontal pressing movement with the band anchored behind.",
        "target_muscles": ["Pectoralis major", "Triceps"],
        "supported_movement_types": [],
        "is_active": False,
        "order": 3,
    },
    {
        "_id": "seated_row",
        "name": "Seated Row",
        "description": "Seated horizontal pulling movement.",
        "target_muscles": ["Latissimus dorsi", "Rhomboids"],
        "supported_movement_types": [],
        "is_active": False,
        "order": 4,
    },
    {
        "_id": "triceps_extension",
        "name": "Triceps Extension",
        "description": "Elbow extension against band resistance.",
        "target_muscles": ["Triceps brachii"],
        "supported_movement_types": [],
        "is_active": False,
        "order": 5,
    },
]


class MongoDB:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.db: AsyncIOMotorDatabase | None = None
        self.connected = False
        self.last_error: str | None = None

    async def connect(self, settings: Settings) -> None:
        self.client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=settings.mongodb_timeout_ms,
            appname="physioband-ai-backend",
            tz_aware=True,
        )
        self.db = self.client[settings.mongodb_db_name]
        try:
            await self.client.admin.command("ping")
            await self.prepare()
            self.connected = True
            self.last_error = None
            log.info("Connected to MongoDB database '%s'", settings.mongodb_db_name)
        except PyMongoError as exc:
            # The API still starts so /health can report the problem; DB routes return 503.
            self.connected = False
            self.last_error = str(exc).split(",")[0]
            log.error("MongoDB connection failed: %s", self.last_error)

    def use(self, client, db_name: str) -> None:
        """Attach an existing client (used by tests with mongomock-motor)."""
        self.client = client
        self.db = client[db_name]
        self.connected = True

    async def prepare(self) -> None:
        assert self.db is not None
        for collection, indexes in INDEXES.items():
            await self.db[collection].create_indexes(indexes)
        for exercise in EXERCISE_SEED:
            await self.db[EXERCISES].update_one({"_id": exercise["_id"]}, {"$set": exercise}, upsert=True)

    async def ping(self) -> bool:
        if self.client is None:
            return False
        try:
            await self.client.admin.command("ping")
            self.connected = True
            return True
        except PyMongoError as exc:
            self.connected = False
            self.last_error = str(exc).split(",")[0]
            return False

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
        self.connected = False


mongodb = MongoDB()
