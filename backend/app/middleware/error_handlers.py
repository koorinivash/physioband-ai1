"""Convert every error into the structured ``{"error": {...}}`` response format."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError, error_body

log = logging.getLogger(__name__)


def _validation_details(exc: RequestValidationError) -> list[dict]:
    details = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", []) if p != "body"]
        details.append({"field": ".".join(loc), "message": err.get("msg", "Invalid value")})
    return details


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        details = _validation_details(exc)
        first = details[0] if details else {"field": "", "message": "Invalid request"}
        message = f"{first['field']}: {first['message']}" if first["field"] else first["message"]
        return JSONResponse(status_code=422, content=error_body("VALIDATION_ERROR", message, details))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 401: "UNAUTHORIZED"}.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(status_code=exc.status_code, content=error_body(code, str(exc.detail)))

    @app.exception_handler(PyMongoError)
    async def database_error(_: Request, exc: PyMongoError):
        log.error("Database error: %s", exc)
        return JSONResponse(
            status_code=503, content=error_body("DATABASE_ERROR", "A database error occurred. Please try again.")
        )

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        log.exception("Unhandled error")
        return JSONResponse(status_code=500, content=error_body("INTERNAL_ERROR", "An unexpected error occurred"))
