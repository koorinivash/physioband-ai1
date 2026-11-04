from __future__ import annotations

import logging

from pymongo.errors import DuplicateKeyError

from app.core.exceptions import AuthError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.user import LoginRequest, RegisterRequest

log = logging.getLogger(__name__)


def public_user(user: dict) -> dict:
    return {k: user[k] for k in ("id", "name", "email", "created_at")} | {"profile": user.get("profile") or {}}


class AuthService:
    def __init__(self, users: UserRepository):
        self.users = users

    async def register(self, data: RegisterRequest) -> dict:
        if await self.users.get_by_email(data.email):
            raise ConflictError("An account with this email already exists", code="EMAIL_ALREADY_REGISTERED")
        try:
            user = await self.users.create(data.name, data.email, hash_password(data.password))
        except DuplicateKeyError:
            raise ConflictError("An account with this email already exists", code="EMAIL_ALREADY_REGISTERED")
        log.info("Registered user %s", user["id"])
        return self._token_response(user)

    async def login(self, data: LoginRequest) -> dict:
        user = await self.users.get_by_email(data.email)
        if not user or not verify_password(data.password, user["password_hash"]):
            raise AuthError("Incorrect email or password", code="INVALID_CREDENTIALS")
        return self._token_response(user)

    @staticmethod
    def _token_response(user: dict) -> dict:
        token, expires_in = create_access_token(user["id"])
        return {"access_token": token, "token_type": "bearer", "expires_in": expires_in, "user": public_user(user)}
