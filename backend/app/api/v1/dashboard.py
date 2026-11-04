from fastapi import APIRouter, Query

from app.api.deps import DB, ML, CurrentUser
from app.schemas.dashboard import DashboardSummary, PerformanceResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard Analytics"])

TZ_QUERY = Query(0, ge=-840, le=840, description="Client UTC offset in minutes (e.g. 330 for IST)")


@router.get("/summary", response_model=DashboardSummary)
async def summary(user: CurrentUser, db: DB, ml: ML, tz_offset_minutes: int = TZ_QUERY):
    return await DashboardService(db, ml).summary(user["id"], tz_offset_minutes)


@router.get("/performance", response_model=PerformanceResponse)
async def performance(
    user: CurrentUser, db: DB, ml: ML, days: int = Query(14, ge=1, le=90), tz_offset_minutes: int = TZ_QUERY
):
    return await DashboardService(db, ml).performance(user["id"], days, tz_offset_minutes)
