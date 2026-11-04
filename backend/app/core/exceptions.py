"""Application errors and the structured error response format.

Every error is returned as:
    {"error": {"code": "SESSION_NOT_FOUND", "message": "...", "details": {...} | null}}
"""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None, details: Any = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class AuthError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ValidationFailed(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class ServiceUnavailable(AppError):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"


def error_body(code: str, message: str, details: Any = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}
