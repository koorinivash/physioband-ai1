from fastapi import APIRouter

from app.api.deps import DB, CurrentUser
from app.core.exceptions import AuthError
from app.core.security import hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.common import MessageResponse
from app.schemas.user import PasswordChange, UserOut, UserUpdate
from app.services.auth_service import public_user

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("/me", response_model=UserOut)
async def get_profile(user: CurrentUser):
    return public_user(user)


@router.patch("/me", response_model=UserOut)
async def update_profile(data: UserUpdate, user: CurrentUser, db: DB):
    fields = {}
    if data.name is not None:
        fields["name"] = data.name.strip()
    if data.profile is not None:
        merged = {**(user.get("profile") or {}), **data.profile.model_dump(exclude_unset=True)}
        fields["profile"] = merged
    updated = await UserRepository(db).update(user["id"], fields) if fields else user
    return public_user(updated)


@router.post("/me/password", response_model=MessageResponse)
async def change_password(data: PasswordChange, user: CurrentUser, db: DB):
    if not verify_password(data.current_password, user["password_hash"]):
        raise AuthError("Current password is incorrect", code="INVALID_CREDENTIALS")
    await UserRepository(db).update(user["id"], {"password_hash": hash_password(data.new_password)})
    return {"message": "Password updated"}
