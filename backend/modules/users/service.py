from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from modules.users.exceptions import (
    CannotChangeOwnRoleError,
    InvalidCurrentPasswordError,
    UserNotFoundError,
)
from modules.users.repository import UserRepository
from modules.users.schemas import (
    PasswordChange,
    UserListResponse,
    UserProfileUpdate,
    UserRead,
    UserRoleUpdate,
    UserSummary,
)
from shared.enums import UserRole
from shared.pagination import make_paginated_response, paginate
from shared.security import hash_password, verify_password


class UserService:
    @staticmethod
    async def list_users(
        session: AsyncSession,
        page: int,
        page_size: int,
        current_user,
        search: Optional[str] = None,
    ) -> UserListResponse:
        offset, limit = paginate(page, page_size)
        users, total = await UserRepository.list_all(session, offset, limit, search=search)
        items = [UserSummary.model_validate(u) for u in users]
        return UserListResponse(**make_paginated_response(items, total, page, limit))

    @staticmethod
    async def update_profile(
        session: AsyncSession, current_user, data: UserProfileUpdate
    ) -> UserRead:
        current_user.name = data.name
        current_user.updated_at = datetime.now(timezone.utc)
        user = await UserRepository.save(session, current_user)
        return UserRead.model_validate(user)

    @staticmethod
    async def change_password(
        session: AsyncSession, current_user, data: PasswordChange
    ) -> None:
        if not verify_password(data.current_password, current_user.password_hash):
            raise InvalidCurrentPasswordError()
        current_user.password_hash = hash_password(data.new_password)
        current_user.updated_at = datetime.now(timezone.utc)
        await UserRepository.save(session, current_user)

    @staticmethod
    async def update_role(
        session: AsyncSession, user_id: UUID, data: UserRoleUpdate, current_user
    ) -> UserSummary:
        if str(user_id) == str(current_user.id):
            raise CannotChangeOwnRoleError()
        user = await UserRepository.find_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError()
        user.role = data.role
        user.updated_at = datetime.now(timezone.utc)
        user = await UserRepository.save(session, user)
        return UserSummary.model_validate(user)
