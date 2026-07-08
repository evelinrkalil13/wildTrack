from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from modules.users.repository import UserRepository
from modules.users.schemas import UserListResponse, UserSummary
from shared.pagination import make_paginated_response, paginate


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
