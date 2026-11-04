from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthError, NotFoundError, ServiceUnavailable
from app.core.security import decode_access_token
from app.database.mongodb import mongodb
from app.repositories.user_repository import UserRepository
from app.services.ml_service import MLService

bearer = HTTPBearer(auto_error=False, description="JWT access token from /auth/login")


def get_db():
    if not mongodb.connected or mongodb.db is None:
        raise ServiceUnavailable(
            "Database is unavailable. Check MONGODB_URI and Atlas network access.", code="DATABASE_UNAVAILABLE"
        )
    return mongodb.db


def get_ml(request: Request) -> MLService:
    return request.app.state.ml


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db=Depends(get_db),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthError("Authentication required", code="NOT_AUTHENTICATED")
    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise AuthError("Session expired, please log in again", code="TOKEN_EXPIRED")
    except jwt.PyJWTError:
        raise AuthError("Invalid authentication token", code="INVALID_TOKEN")
    try:
        user = await UserRepository(db).get_by_id(user_id)
    except NotFoundError:  # malformed id inside a validly signed token
        user = None
    if not user:
        raise AuthError("User no longer exists", code="INVALID_TOKEN")
    return user


DB = Annotated[object, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
ML = Annotated[MLService, Depends(get_ml)]
AppSettings = Annotated[Settings, Depends(get_settings)]
