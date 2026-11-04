from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.repositories.workout_repository import WorkoutRepository
from app.services.ml_service import MLService
from app.services.quality_service import quality_of


def _local_midnight_utc(now_utc: datetime, tz_offset_minutes: int) -> datetime:
    local = now_utc + timedelta(minutes=tz_offset_minutes)
    midnight_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight_local - timedelta(minutes=tz_offset_minutes)


def _aggregate(sessions: list[dict]) -> dict:
    total = sum(s["total_reps"] for s in sessions)
    correct = sum(s["correct_reps"] for s in sessions)
    incorrect = sum(s["incorrect_reps"] for s in sessions)
    weighted = [(s["avg_tension_n"], s["total_reps"]) for s in sessions if s.get("avg_tension_n") is not None and s["total_reps"]]
    reps_with_tension = sum(w for _, w in weighted)
    return {
        "sessions": len(sessions),
        "total_reps": total,
        "correct_reps": correct,
        "incorrect_reps": incorrect,
        "quality_score": quality_of(correct, total, incorrect),
        "active_minutes": round(sum(s.get("duration_s") or 0 for s in sessions) / 60.0, 1),
        "avg_tension_n": round(sum(t * w for t, w in weighted) / reps_with_tension, 2) if reps_with_tension else None,
    }


class DashboardService:
    def __init__(self, db, ml: MLService):
        self.sessions = WorkoutRepository(db)
        self.ml = ml

    async def summary(self, user_id: str, tz_offset_minutes: int) -> dict:
        now = datetime.now(timezone.utc)
        all_finished = await self.sessions.finished_since(user_id, None)
        today_start = _local_midnight_utc(now, tz_offset_minutes)
        today = [s for s in all_finished if s["start_time"] >= today_start]
        recent, _ = await self.sessions.page(user_id, 1, 5, None, None)
        active = await self.sessions.active_for_user(user_id)
        return {
            "today": _aggregate(today),
            "all_time": _aggregate(all_finished),
            "recent_sessions": recent,
            "active_session_id": active[0]["id"] if active else None,
            "model": self.ml.status(),
        }

    async def performance(self, user_id: str, days: int, tz_offset_minutes: int) -> dict:
        now = datetime.now(timezone.utc)
        start = _local_midnight_utc(now, tz_offset_minutes) - timedelta(days=days - 1)
        sessions = await self.sessions.finished_since(user_id, start)

        by_day: dict[str, list[dict]] = defaultdict(list)
        for s in sessions:
            local_day = (s["start_time"] + timedelta(minutes=tz_offset_minutes)).date().isoformat()
            by_day[local_day].append(s)

        points = []
        for i in range(days):
            day = (start + timedelta(minutes=tz_offset_minutes) + timedelta(days=i)).date().isoformat()
            agg = _aggregate(by_day.get(day, []))
            points.append({"date": day, **{k: agg[k] for k in ("sessions", "total_reps", "correct_reps", "quality_score", "avg_tension_n")}})

        scored = [p["quality_score"] for p in points if p["quality_score"] is not None]
        trend = None
        if len(scored) >= 2:
            half = len(scored) // 2
            trend = round(sum(scored[half:]) / len(scored[half:]) - sum(scored[:half]) / half, 1)
        return {
            "days": days,
            "points": points,
            "quality_trend": trend,
            "best_quality": max(scored) if scored else None,
            "total_reps": sum(p["total_reps"] for p in points),
        }
