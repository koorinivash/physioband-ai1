from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from app.core.exceptions import NotFoundError


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_object_id(value: str, what: str = "resource") -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise NotFoundError(f"{what.capitalize()} not found", code=f"{what.upper().replace(' ', '_')}_NOT_FOUND")


def serialize(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert a Mongo document to API form: ``_id`` -> ``id`` and ObjectIds -> strings."""
    if doc is None:
        return None
    out: dict[str, Any] = {}
    for key, value in doc.items():
        if key == "_id":
            out["id"] = str(value)
        elif isinstance(value, ObjectId):
            out[key] = str(value)
        elif isinstance(value, datetime) and value.tzinfo is None:
            out[key] = value.replace(tzinfo=timezone.utc)  # Mongo stores UTC without tzinfo
        else:
            out[key] = value
    return out
