from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import APIModel

PASSWORD_FIELD = Field(min_length=8, max_length=64)


def check_password_strength(v: str) -> str:
    if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one letter and one number")
    return v


class UserProfile(APIModel):
    age: int | None = Field(default=None, ge=10, le=100)
    gender: Literal["male", "female", "other", "prefer_not_to_say"] | None = None
    height_cm: float | None = Field(default=None, ge=80, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=300)
    dominant_arm: Literal["left", "right"] | None = None
    training_arm: Literal["left", "right"] | None = None


class RegisterRequest(APIModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = PASSWORD_FIELD

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must contain at least 2 characters")
        return v

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        return check_password_strength(v)


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=64)


class UserOut(APIModel):
    id: str
    name: str
    email: EmailStr
    created_at: datetime
    profile: UserProfile = Field(default_factory=UserProfile)


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class UserUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    profile: UserProfile | None = None


class PasswordChange(APIModel):
    current_password: str = Field(min_length=1, max_length=64)
    new_password: str = PASSWORD_FIELD

    @field_validator("new_password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        return check_password_strength(v)
