from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, select
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
    async def list_all(
        session: AsyncSession,
        offset: int,
        limit: int,
        search: Optional[str] = None,
    ) -> tuple[list[User], int]:
        conditions = [User.deleted_at.is_(None)]
        if search:
            pattern = f"%{search}%"
            conditions.append(or_(User.name.ilike(pattern), User.email.ilike(pattern)))

        stmt = select(User).where(*conditions)
        count_result = await session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar_one()

        result = await session.execute(
            stmt.order_by(User.name).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def create(session: AsyncSession, data: dict) -> User:
        user = User(**data)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
