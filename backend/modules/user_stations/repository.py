from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.user_stations.models import UserStation
from shared.enums import StationUserRole


class UserStationRepository:
    @staticmethod
    async def create(session: AsyncSession, user_station: UserStation) -> UserStation:
        session.add(user_station)
        await session.commit()
        await session.refresh(user_station)
        return user_station

    @staticmethod
    async def find_by_id(
        session: AsyncSession, us_id: UUID
    ) -> Optional[UserStation]:
        result = await session.execute(
            select(UserStation).where(
                UserStation.id == us_id,
                UserStation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_id_in_station(
        session: AsyncSession, us_id: UUID, station_id: UUID
    ) -> Optional[UserStation]:
        result = await session.execute(
            select(UserStation).where(
                UserStation.id == us_id,
                UserStation.station_id == station_id,
                UserStation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_user_and_station(
        session: AsyncSession, user_id: UUID, station_id: UUID
    ) -> Optional[UserStation]:
        result = await session.execute(
            select(UserStation).where(
                UserStation.user_id == user_id,
                UserStation.station_id == station_id,
                UserStation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def user_has_access(
        session: AsyncSession, user_id: UUID, station_id: UUID
    ) -> bool:
        result = await session.execute(
            select(func.count())
            .select_from(UserStation)
            .where(
                UserStation.user_id == user_id,
                UserStation.station_id == station_id,
                UserStation.deleted_at.is_(None),
            )
        )
        return result.scalar_one() > 0

    @staticmethod
    async def get_user_role_in_station(
        session: AsyncSession, user_id: UUID, station_id: UUID
    ) -> Optional[StationUserRole]:
        result = await session.execute(
            select(UserStation.role).where(
                UserStation.user_id == user_id,
                UserStation.station_id == station_id,
                UserStation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_station_with_users(
        session: AsyncSession,
        station_id: UUID,
        offset: int,
        limit: int,
    ) -> tuple[list[tuple], int]:
        from modules.users.models import User

        conditions = [
            UserStation.station_id == station_id,
            UserStation.deleted_at.is_(None),
        ]

        base = select(UserStation).where(*conditions)
        count_result = await session.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        result = await session.execute(
            select(UserStation, User.name, User.email)
            .join(User, UserStation.user_id == User.id)
            .where(*conditions)
            .order_by(UserStation.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.all()), total

    @staticmethod
    async def update(session: AsyncSession, user_station: UserStation) -> UserStation:
        await session.commit()
        await session.refresh(user_station)
        return user_station

    @staticmethod
    async def soft_delete_one(session: AsyncSession, user_station: UserStation) -> None:
        user_station.deleted_at = datetime.now(timezone.utc)
        await session.commit()

    @staticmethod
    async def soft_delete_all_for_station(
        session: AsyncSession, station_id: UUID
    ) -> None:
        now = datetime.now(timezone.utc)
        await session.execute(
            update(UserStation)
            .where(
                UserStation.station_id == station_id,
                UserStation.deleted_at.is_(None),
            )
            .values(deleted_at=now)
        )
        await session.commit()
