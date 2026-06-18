from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.users.models import User


class UserRepository:
    @staticmethod
    async def find_by_id(session: AsyncSession, user_id: str | UUID) -> User | None:
        result = await session.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_email(session: AsyncSession, email: str) -> User | None:
        result = await session.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(session: AsyncSession, data: dict) -> User:
        user = User(**data)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
