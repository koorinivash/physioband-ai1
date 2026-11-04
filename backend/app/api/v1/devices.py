from fastapi import APIRouter, status

from app.api.deps import DB, CurrentUser
from app.core.exceptions import NotFoundError
from app.repositories.device_repository import DeviceRepository
from app.schemas.common import MessageResponse
from app.schemas.device import DeviceOut, DeviceRegister

router = APIRouter(prefix="/devices", tags=["Device Management"])


@router.post("/register", response_model=DeviceOut, status_code=status.HTTP_200_OK)
async def register_device(data: DeviceRegister, user: CurrentUser, db: DB):
    """Register a PhysioBand ESP32 (or refresh its details on every BLE connection)."""
    return await DeviceRepository(db).upsert(user["id"], data.model_dump())


@router.get("", response_model=list[DeviceOut])
async def list_devices(user: CurrentUser, db: DB):
    return await DeviceRepository(db).list_for_user(user["id"])


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(device_id: str, user: CurrentUser, db: DB):
    device = await DeviceRepository(db).get(user["id"], device_id)
    if not device:
        raise NotFoundError("Device not found", code="DEVICE_NOT_FOUND")
    return device


@router.delete("/{device_id}", response_model=MessageResponse)
async def forget_device(device_id: str, user: CurrentUser, db: DB):
    if not await DeviceRepository(db).delete(user["id"], device_id):
        raise NotFoundError("Device not found", code="DEVICE_NOT_FOUND")
    return {"message": "Device removed"}
