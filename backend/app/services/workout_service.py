"""Workout session lifecycle: start -> stream sensor batches (live analysis) -> complete.

Live analysis re-runs the pipeline over all samples received so far (a typical
workout is only a few thousand samples) and reports reps that are newly complete.
Completing a session runs a final analysis whose result is authoritative.
BLE interruptions are handled by keeping the session "active" while batches stop
arriving, and by closing it as "interrupted" when the app reports a disconnect or
when the user starts a new workout.
"""
from __future__ import annotations

import logging
import math

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationFailed
from app.repositories.base import utcnow
from app.repositories.device_repository import DeviceRepository
from app.repositories.exercise_repository import ExerciseRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.sensor_repository import SensorRepository
from app.repositories.workout_repository import WorkoutRepository
from app.schemas.sensor import SensorBatch
from app.schemas.workout import WorkoutStart
from app.services.ml_service import MLService
from app.services.quality_service import empty_session_fields, session_fields_from_analysis

log = logging.getLogger(__name__)
MIN_ANALYSIS_SAMPLES = 10


class WorkoutService:
    def __init__(self, db, ml: MLService, settings: Settings):
        self.sessions = WorkoutRepository(db)
        self.sensors = SensorRepository(db)
        self.feedback = FeedbackRepository(db)
        self.exercises = ExerciseRepository(db)
        self.devices = DeviceRepository(db)
        self.ml = ml
        self.settings = settings

    async def _get_owned(self, user_id: str, session_id: str) -> dict:
        session = await self.sessions.get(user_id, session_id)
        if not session:
            raise NotFoundError("Workout session not found", code="SESSION_NOT_FOUND")
        return session

    async def start(self, user_id: str, data: WorkoutStart) -> dict:
        exercise = await self.exercises.get(data.exercise_id)
        if not exercise:
            raise NotFoundError("Exercise not found", code="EXERCISE_NOT_FOUND")
        if not exercise["is_active"]:
            raise ValidationFailed(f"{exercise['name']} is not available yet", code="EXERCISE_NOT_AVAILABLE")
        if data.device_id and not await self.devices.get(user_id, data.device_id):
            raise NotFoundError("Device is not registered to this account", code="DEVICE_NOT_FOUND")

        # Only one active workout per user: close any session left open by a crash / lost connection.
        for old in await self.sessions.active_for_user(user_id):
            log.info("Closing stale active session %s", old["id"])
            await self._finalize(old, "superseded")

        session = await self.sessions.create(user_id, exercise, data.device_id)
        log.info("Started workout %s (%s) for user %s", session["id"], exercise["id"], user_id)
        return session

    async def ingest(self, user_id: str, session_id: str, batch: SensorBatch) -> dict:
        session = await self._get_owned(user_id, session_id)
        if session["status"] != "active":
            raise ConflictError("Workout session is not active", code="SESSION_NOT_ACTIVE")
        if len(batch.samples) > self.settings.max_samples_per_batch:
            raise ValidationFailed(
                f"Batch too large ({len(batch.samples)} samples, max {self.settings.max_samples_per_batch})",
                code="BATCH_TOO_LARGE",
            )
        if session["sample_count"] + len(batch.samples) > self.settings.max_samples_per_session:
            raise ValidationFailed("Session sample limit reached; complete this workout", code="SESSION_FULL")

        samples = [s.model_dump() for s in batch.samples]
        for s in samples:  # JSON cannot carry NaN/inf, but guard anyway
            s["ua"] = [v if v is None or math.isfinite(v) else None for v in s["ua"]]
            s["fa"] = [v if v is None or math.isfinite(v) else None for v in s["fa"]]
            if s["force_n"] is not None and not math.isfinite(s["force_n"]):
                s["force_n"] = None

        stored = await self.sensors.insert_batch(
            session_id, user_id, batch.batch_seq, batch.device_id or session["device_id"], batch.protocol_version, samples
        )
        if stored:
            await self.sessions.add_samples(session_id, len(samples))
        total = session["sample_count"] + (len(samples) if stored else 0)

        response = {
            "session_id": session_id,
            "batch_seq": batch.batch_seq,
            "accepted": stored,
            "duplicate": not stored,
            "stored_samples": len(samples) if stored else 0,
            "total_samples": total,
            "analysis": None,
            "analysis_error": None,
        }
        if batch.analyze and total >= MIN_ANALYSIS_SAMPLES:
            try:
                response["analysis"] = await self._live_analysis(session)
            except ValidationFailed as exc:
                response["analysis_error"] = exc.message
        return response

    async def _live_analysis(self, session: dict) -> dict:
        samples = await self.sensors.load_samples(session["id"])
        analysis = await self.ml.analyze(samples, session["exercise_id"], mode="live")
        known = await self.feedback.known_rep_numbers(session["id"])
        new_reps = [r for r in analysis["reps"] if r["number"] not in known]
        await self.feedback.upsert_reps(session["id"], new_reps)
        analysis["new_reps"] = new_reps
        await self.sessions.update(session["id"], session_fields_from_analysis(analysis))
        return analysis

    async def analyze(self, user_id: str, session_id: str) -> dict:
        session = await self._get_owned(user_id, session_id)
        samples = await self.sensors.load_samples(session_id)
        if len(samples) < MIN_ANALYSIS_SAMPLES:
            raise ValidationFailed("Not enough sensor data has been received for analysis", code="INSUFFICIENT_DATA")
        analysis = await self.ml.analyze(samples, session["exercise_id"], mode="final")
        await self._store_final(session_id, analysis)
        return analysis

    async def _store_final(self, session_id: str, analysis: dict) -> None:
        await self.feedback.upsert_reps(session_id, analysis["reps"])
        await self.feedback.delete_from(session_id, len(analysis["reps"]) + 1)
        await self.sessions.update(session_id, session_fields_from_analysis(analysis))

    async def complete(self, user_id: str, session_id: str, end_reason: str) -> dict:
        session = await self._get_owned(user_id, session_id)
        if session["status"] != "active":
            return await self.detail(user_id, session_id)  # idempotent: already closed
        await self._finalize(session, end_reason)
        return await self.detail(user_id, session_id)

    async def _finalize(self, session: dict, end_reason: str) -> None:
        fields: dict
        samples = await self.sensors.load_samples(session["id"])
        if len(samples) >= MIN_ANALYSIS_SAMPLES:
            try:
                analysis = await self.ml.analyze(samples, session["exercise_id"], mode="final")
                await self._store_final(session["id"], analysis)
                fields = {}
            except ValidationFailed as exc:
                fields = empty_session_fields(f"Sensor data could not be analysed: {exc.message}")
        else:
            fields = empty_session_fields("No sensor data was received during this workout.")

        end = utcnow()
        fields.update(
            {
                "status": "completed" if end_reason == "user_completed" else "interrupted",
                "end_reason": end_reason,
                "end_time": end,
                "duration_s": round((end - session["start_time"]).total_seconds(), 1),
            }
        )
        await self.sessions.update(session["id"], fields)
        log.info("Workout %s closed (%s)", session["id"], end_reason)

    async def list(self, user_id: str, page: int, page_size: int, exercise_id: str | None, status: str | None) -> dict:
        items, total = await self.sessions.page(user_id, page, page_size, exercise_id, status)
        return {"items": items, "page": page, "page_size": page_size, "total": total,
                "pages": max(1, math.ceil(total / page_size))}

    async def detail(self, user_id: str, session_id: str) -> dict:
        session = await self._get_owned(user_id, session_id)
        feedback = await self.feedback.list_for_session(session_id)
        return {**session, "feedback": feedback}
