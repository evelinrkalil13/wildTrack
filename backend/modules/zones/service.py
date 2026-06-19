from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from modules.zones.exceptions import (
    ZoneHasActiveStationsError,
    ZoneNameConflictError,
    ZoneNotFoundError,
)
from modules.zones.models import Zone
from modules.zones.repository import ZoneRepository
from modules.zones.schemas import ZoneCreate, ZoneListResponse, ZoneRead, ZoneUpdate
from shared.pagination import make_paginated_response, paginate
from shared.uuid7 import generate_uuid7


class ZoneService:
    @staticmethod
    async def create_zone(session: AsyncSession, data: ZoneCreate) -> ZoneRead:
        existing = await ZoneRepository.find_by_name_and_country(
            session, data.name, data.country
        )
        if existing:
            raise ZoneNameConflictError()

        zone = Zone(
            id=generate_uuid7(),
            name=data.name,
            municipality=data.municipality,
            city=data.city,
            country=data.country,
            altitude=data.altitude,
            latitude=data.latitude,
            longitude=data.longitude,
            geom=ZoneRepository.build_geom(data.latitude, data.longitude),
        )
        zone = await ZoneRepository.create(session, zone)
        return ZoneRead.model_validate(zone)

    @staticmethod
    async def get_zone(session: AsyncSession, zone_id: UUID) -> ZoneRead:
        zone = await ZoneRepository.find_by_id(session, zone_id)
        if zone is None:
            raise ZoneNotFoundError()
        return ZoneRead.model_validate(zone)

    @staticmethod
    async def list_zones(
        session: AsyncSession,
        page: int,
        page_size: int,
        country: str | None = None,
    ) -> ZoneListResponse:
        offset, limit = paginate(page, page_size)
        zones, total = await ZoneRepository.list_all(session, offset, limit, country=country)
        items = [ZoneRead.model_validate(z) for z in zones]
        return ZoneListResponse(**make_paginated_response(items, total, page, limit))

    @staticmethod
    async def update_zone(
        session: AsyncSession, zone_id: UUID, data: ZoneUpdate
    ) -> ZoneRead:
        zone = await ZoneRepository.find_by_id(session, zone_id)
        if zone is None:
            raise ZoneNotFoundError()

        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data or "country" in update_data:
            new_name = update_data.get("name", zone.name)
            new_country = update_data.get("country", zone.country)
            conflict = await ZoneRepository.find_by_name_and_country(
                session, new_name, new_country, exclude_id=zone_id
            )
            if conflict:
                raise ZoneNameConflictError()

        for field, value in update_data.items():
            setattr(zone, field, value)

        if "latitude" in update_data or "longitude" in update_data:
            zone.geom = ZoneRepository.build_geom(zone.latitude, zone.longitude)

        zone = await ZoneRepository.update(session, zone)
        return ZoneRead.model_validate(zone)

    @staticmethod
    async def delete_zone(session: AsyncSession, zone_id: UUID) -> None:
        zone = await ZoneRepository.find_by_id(session, zone_id)
        if zone is None:
            raise ZoneNotFoundError()
        if await ZoneRepository.has_active_stations(session, zone_id):
            raise ZoneHasActiveStationsError()
        await ZoneRepository.soft_delete(session, zone)
