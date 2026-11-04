from fastapi import APIRouter, status

from app.api.deps import DB, CurrentUser
from app.repositories.user_repository import UserRepository
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.auth_service import AuthService, public_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: DB):
    """Create an account and return an access token."""
    return await AuthService(UserRepository(db)).register(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: DB):
    return await AuthService(UserRepository(db)).login(data)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return public_user(user)
