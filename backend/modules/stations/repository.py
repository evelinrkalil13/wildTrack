from typing import Optional
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.stations.models import Station
from shared.enums import StationStatus


class StationRepository:
    @staticmethod
    async def find_by_id(
        session: AsyncSession, station_id: UUID
    ) -> Optional[Station]:
        result = await session.execute(
            select(Station).where(
                Station.id == station_id, Station.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_code(
        session: AsyncSession, code: str
    ) -> Optional[Station]:
        result = await session.execute(
            select(Station).where(
                func.lower(Station.code) == code.lower(),
                Station.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(
        session: AsyncSession,
        offset: int,
        limit: int,
        zone_id: Optional[UUID] = None,
        status: Optional[StationStatus] = None,
    ) -> tuple[list[Station], int]:
        base = select(Station).where(Station.deleted_at.is_(None))
        if zone_id is not None:
            base = base.where(Station.zone_id == zone_id)
        if status is not None:
            base = base.where(Station.status == status)
        count_result = await session.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()
        result = await session.execute(base.offset(offset).limit(limit))
        return list(result.scalars().all()), total

    @staticmethod
    async def list_for_user(
        session: AsyncSession,
        user_id: UUID,
        offset: int,
        limit: int,
        zone_id: Optional[UUID] = None,
        status: Optional[StationStatus] = None,
    ) -> tuple[list[Station], int]:
        from modules.user_stations.models import UserStation

        base = select(Station).where(
            Station.deleted_at.is_(None),
            select(UserStation.id)
            .where(
                UserStation.station_id == Station.id,
                UserStation.user_id == user_id,
                UserStation.deleted_at.is_(None),
            )
            .exists(),
        )
        if zone_id is not None:
            base = base.where(Station.zone_id == zone_id)
        if status is not None:
            base = base.where(Station.status == status)
        count_result = await session.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()
        result = await session.execute(base.offset(offset).limit(limit))
        return list(result.scalars().all()), total

    @staticmethod
    async def create(session: AsyncSession, station: Station) -> Station:
        session.add(station)
        await session.commit()
        await session.refresh(station)
        return station

    @staticmethod
    async def update(session: AsyncSession, station: Station) -> Station:
        await session.commit()
        await session.refresh(station)
        return station

    @staticmethod
    async def soft_delete(session: AsyncSession, station: Station) -> None:
        from datetime import datetime, timezone

        station.deleted_at = datetime.now(timezone.utc)
        await session.commit()

    @staticmethod
    def build_geom(latitude: float, longitude: float) -> WKTElement:
        return WKTElement(f"POINT({longitude} {latitude})", srid=4326)
