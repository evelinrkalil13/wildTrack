from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.foods.models import Food


class FoodRepository:
    @staticmethod
    async def find_by_id(session: AsyncSession, food_id: UUID) -> Optional[Food]:
        result = await session.execute(
            select(Food).where(Food.id == food_id, Food.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_name(session: AsyncSession, name: str) -> Optional[Food]:
        result = await session.execute(
            select(Food).where(
                Food.name == name,
                Food.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(
        session: AsyncSession,
        offset: int,
        limit: int,
    ) -> tuple[list[Food], int]:
        conditions = [Food.deleted_at.is_(None)]

        base = select(Food).where(*conditions)
        count_result = await session.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        result = await session.execute(
            base.order_by(Food.name.asc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def create(session: AsyncSession, food: Food) -> Food:
        session.add(food)
        await session.commit()
        await session.refresh(food)
        return food

    @staticmethod
    async def update(session: AsyncSession, food: Food) -> Food:
        await session.commit()
        await session.refresh(food)
        return food

    @staticmethod
    async def soft_delete(session: AsyncSession, food: Food) -> None:
        food.deleted_at = datetime.now(timezone.utc)
        await session.commit()
