from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.station_foods.models import StationFood


class StationFoodRepository:
    @staticmethod
    async def find_by_id(
        session: AsyncSession, sf_id: UUID
    ) -> Optional[StationFood]:
        result = await session.execute(
            select(StationFood).where(StationFood.id == sf_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_id_in_station(
        session: AsyncSession, sf_id: UUID, station_id: UUID
    ) -> Optional[StationFood]:
        result = await session.execute(
            select(StationFood).where(
                StationFood.id == sf_id,
                StationFood.station_id == station_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_station_and_food(
        session: AsyncSession, station_id: UUID, food_id: UUID
    ) -> Optional[StationFood]:
        result = await session.execute(
            select(StationFood).where(
                StationFood.station_id == station_id,
                StationFood.food_id == food_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_active_for_station(
        session: AsyncSession, station_id: UUID
    ) -> Optional[StationFood]:
        result = await session.execute(
            select(StationFood).where(
                StationFood.station_id == station_id,
                StationFood.active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def has_active_for_food(session: AsyncSession, food_id: UUID) -> bool:
        result = await session.execute(
            select(func.count())
            .select_from(StationFood)
            .where(StationFood.food_id == food_id, StationFood.active.is_(True))
        )
        return result.scalar_one() > 0

    @staticmethod
    async def list_for_station_with_food(
        session: AsyncSession,
        station_id: UUID,
        offset: int,
        limit: int,
    ) -> tuple[list[tuple], int]:
        from modules.foods.models import Food

        conditions = [StationFood.station_id == station_id]

        base = select(StationFood).where(*conditions)
        count_result = await session.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        result = await session.execute(
            select(StationFood, Food.name, Food.type)
            .join(Food, StationFood.food_id == Food.id)
            .where(*conditions)
            .order_by(StationFood.active.desc(), StationFood.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.all()), total

    @staticmethod
    async def find_by_id_in_station_with_food(
        session: AsyncSession, sf_id: UUID, station_id: UUID
    ) -> Optional[tuple]:
        from modules.foods.models import Food

        result = await session.execute(
            select(StationFood, Food.name, Food.type)
            .join(Food, StationFood.food_id == Food.id)
            .where(
                StationFood.id == sf_id,
                StationFood.station_id == station_id,
            )
        )
        return result.one_or_none()

    @staticmethod
    async def list_stations_by_food(
        session: AsyncSession, food_id: UUID
    ) -> list[tuple]:
        from modules.stations.models import Station

        result = await session.execute(
            select(StationFood.station_id, Station.code, Station.name, StationFood.active, StationFood.created_at)
            .join(Station, StationFood.station_id == Station.id)
            .where(StationFood.food_id == food_id)
            .order_by(StationFood.active.desc(), StationFood.created_at.desc())
        )
        return list(result.all())

    @staticmethod
    async def deactivate(session: AsyncSession, sf: StationFood) -> None:
        """Set active=False and flush immediately so the unique index is satisfied
        before the subsequent activation UPDATE is sent in the same transaction."""
        sf.active = False
        await session.flush()

    @staticmethod
    async def create(session: AsyncSession, sf: StationFood) -> StationFood:
        session.add(sf)
        await session.commit()
        await session.refresh(sf)
        return sf

    @staticmethod
    async def update(session: AsyncSession, sf: StationFood) -> StationFood:
        await session.commit()
        await session.refresh(sf)
        return sf

    @staticmethod
    async def hard_delete(session: AsyncSession, sf: StationFood) -> None:
        await session.delete(sf)
        await session.commit()
