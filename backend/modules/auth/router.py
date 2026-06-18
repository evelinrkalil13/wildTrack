from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from infrastructure.postgres import get_db_session
from modules.auth.schemas import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from modules.auth.service import AuthService
from modules.users.models import User
from modules.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, session: AsyncSession = Depends(get_db_session)):
    user = await AuthService.register(session, data)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_db_session)):
    return await AuthService.login(session, data)


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
