"""PhysioBand AI FastAPI application.

Run (from the backend folder, with the virtual environment active):
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Swagger UI: http://localhost:8000/docs
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.mongodb import mongodb
from app.middleware.error_handlers import register_error_handlers
from app.middleware.request_logging import RequestLoggingMiddleware
from app.services.ml_service import MLService

log = logging.getLogger(__name__)


def create_app(connect_database: bool = True) -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    if not settings.jwt_secret_key.strip():
        # PyJWT refuses empty HMAC keys, so every login/register would fail with a 500.
        raise RuntimeError(
            "JWT_SECRET_KEY is empty. Set it to a long random value, e.g. "
            "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    if len(settings.jwt_secret_key) < 32 or settings.jwt_secret_key in ("change-me-in-env", "replace-with-a-long-random-secret"):
        if settings.environment == "production":
            raise RuntimeError("JWT_SECRET_KEY must be set to a strong random value in production")
        log.warning("Using a default JWT_SECRET_KEY - set a random secret in backend/.env")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.ml.load_model()
        if connect_database:
            await mongodb.connect(settings)
        yield
        if connect_database:
            mongodb.close()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Backend for PhysioBand AI - resistance-exercise quality monitoring. "
            "Receives ESP32 sensor data relayed by the mobile app, runs the Python ML pipeline "
            "(repetition counting + quality classification) and stores workouts in MongoDB Atlas. "
            "Not a medical device; results are not a clinical assessment."
        ),
        lifespan=lifespan,
    )
    app.state.ml = MLService(settings)

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["Health"])
    async def health():
        db_ok = await mongodb.ping()
        return {
            "status": "ok" if db_ok else "degraded",
            "version": __version__,
            "database": {"connected": db_ok, "error": None if db_ok else mongodb.last_error},
            "model": app.state.ml.status(),
        }

    return app


app = create_app()
