from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, require_admin
from infrastructure.postgres import get_db_session
from modules.users.schemas import (
    PasswordChange,
    UserListResponse,
    UserProfileUpdate,
    UserRead,
    UserRoleUpdate,
    UserSummary,
)
from modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(require_admin),
):
    return await UserService.list_users(
        session, page, page_size, current_user, search=search
    )


@router.patch("/me", response_model=UserRead)
async def update_profile(
    data: UserProfileUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await UserService.update_profile(session, current_user, data)


@router.patch("/me/password", status_code=204)
async def change_password(
    data: PasswordChange,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    await UserService.change_password(session, current_user, data)


@router.patch("/{user_id}/role", response_model=UserSummary)
async def update_user_role(
    user_id: UUID,
    data: UserRoleUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(require_admin),
):
    return await UserService.update_role(session, user_id, data, current_user)
