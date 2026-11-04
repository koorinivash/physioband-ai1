"""Sensor sample format sent by the mobile app (decoded from the ESP32 BLE packets).

    ua / fa = [accel_x_g, accel_y_g, accel_z_g, gyro_x_dps, gyro_y_dps, gyro_z_dps]
    force_n = resistance-band tension in newtons
    status  = bit flags from the firmware (bit0 upper-arm IMU OK, bit1 forearm IMU OK,
              bit2 load cell OK, bit3 load cell calibrated)
A null value marks a reading the app or firmware flagged as invalid.
"""
from __future__ import annotations

from pydantic import Field

from app.schemas.common import APIModel

ImuVector = list[float | None]


class SensorSample(APIModel):
    timestamp_ms: int = Field(ge=0, description="ESP32 millis() at sampling time")
    ua: ImuVector = Field(min_length=6, max_length=6, description="Upper-arm MPU6050 (0x68)")
    fa: ImuVector = Field(min_length=6, max_length=6, description="Forearm MPU6050 (0x69)")
    force_n: float | None = Field(description="Load-cell tension in N")
    status: int = Field(default=15, ge=0, le=255)


class SensorBatch(APIModel):
    batch_seq: int = Field(ge=0, description="Increments per upload; duplicates are ignored")
    device_id: str | None = Field(default=None, max_length=40)
    protocol_version: int = Field(default=1, ge=1, le=255)
    samples: list[SensorSample] = Field(min_length=1)
    analyze: bool = Field(default=True, description="Return live analysis with the response")
