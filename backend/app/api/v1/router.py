from fastapi import APIRouter

from app.api.v1 import auth, dashboard, devices, exercises, ml, users, workouts

api_router = APIRouter()
for module in (auth, users, devices, exercises, workouts, ml, dashboard):
    api_router.include_router(module.router)
