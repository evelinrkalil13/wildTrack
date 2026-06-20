from typing import Optional
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.zones.models import Zone


class ZoneRepository:
    @staticmethod
    async def find_by_id(session: AsyncSession, zone_id: UUID) -> Optional[Zone]:
        result = await session.execute(
            select(Zone).where(Zone.id == zone_id, Zone.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_name_and_country(
        session: AsyncSession, name: str, country: str, exclude_id: Optional[UUID] = None
    ) -> Optional[Zone]:
        stmt = select(Zone).where(
            func.lower(Zone.name) == name.lower(),
            func.lower(Zone.country) == country.lower(),
            Zone.deleted_at.is_(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(Zone.id != exclude_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(
        session: AsyncSession,
        offset: int,
        limit: int,
        country: Optional[str] = None,
    ) -> tuple[list[Zone], int]:
        base = select(Zone).where(Zone.deleted_at.is_(None))
        if country is not None:
            base = base.where(func.lower(Zone.country) == country.lower())
        count_result = await session.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()
        result = await session.execute(base.offset(offset).limit(limit))
        return list(result.scalars().all()), total

    @staticmethod
    async def create(session: AsyncSession, zone: Zone) -> Zone:
        session.add(zone)
        await session.commit()
        await session.refresh(zone)
        return zone

    @staticmethod
    async def update(session: AsyncSession, zone: Zone) -> Zone:
        await session.commit()
        await session.refresh(zone)
        return zone

    @staticmethod
    async def soft_delete(session: AsyncSession, zone: Zone) -> None:
        from datetime import datetime, timezone
        zone.deleted_at = datetime.now(timezone.utc)
        await session.commit()

    @staticmethod
    async def has_active_stations(session: AsyncSession, zone_id: UUID) -> bool:
        from modules.stations.models import Station

        result = await session.execute(
            select(func.count()).select_from(
                select(Station)
                .where(Station.zone_id == zone_id, Station.deleted_at.is_(None))
                .subquery()
            )
        )
        return result.scalar_one() > 0

    @staticmethod
    def build_geom(latitude: float, longitude: float) -> WKTElement:
        return WKTElement(f"POINT({longitude} {latitude})", srid=4326)
