from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel


class DeviceRegister(APIModel):
    device_id: str = Field(pattern=r"^[A-Za-z0-9_-]{3,40}$", examples=["PB-3C61A2F0"])
    device_name: str = Field(min_length=1, max_length=60, examples=["PhysioBand-A2F0"])
    firmware_version: str = Field(default="unknown", max_length=20, examples=["1.0.0"])
    protocol_version: int = Field(default=1, ge=1, le=255)
    ble_address: str | None = Field(default=None, max_length=64, description="BLE MAC / platform identifier")
    sample_rate_hz: int | None = Field(default=None, ge=1, le=500)


class DeviceOut(APIModel):
    id: str
    device_id: str
    device_name: str
    firmware_version: str
    protocol_version: int
    ble_address: str | None = None
    sample_rate_hz: int | None = None
    registered_at: datetime
    last_connected_at: datetime | None = None
