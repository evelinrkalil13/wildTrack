from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from modules.stations.exceptions import (
    StationAccessDeniedError,
    StationCodeConflictError,
    StationNotFoundError,
)
from modules.stations.models import Station
from modules.stations.repository import StationRepository
from modules.stations.schemas import (
    StationCreate,
    StationListResponse,
    StationRead,
    StationUpdate,
)
from modules.user_stations.models import UserStation
from modules.user_stations.repository import UserStationRepository
from modules.zones.exceptions import ZoneNotFoundError
from modules.zones.repository import ZoneRepository
from shared.enums import StationStatus, StationUserRole, UserRole
from shared.pagination import make_paginated_response, paginate
from shared.uuid7 import generate_uuid7


def _is_admin(user) -> bool:
    role_val = user.role.value if hasattr(user.role, "value") else user.role
    return role_val == UserRole.admin.value


class StationService:
    @staticmethod
    async def create_station(
        session: AsyncSession, data: StationCreate, current_user
    ) -> StationRead:
        zone = await ZoneRepository.find_by_id(session, data.zone_id)
        if zone is None:
            raise ZoneNotFoundError()

        existing = await StationRepository.find_by_code(session, data.code)
        if existing is not None:
            raise StationCodeConflictError()

        station = Station(
            id=generate_uuid7(),
            code=data.code,
            name=data.name,
            zone_id=data.zone_id,
            latitude=data.latitude,
            longitude=data.longitude,
            geom=StationRepository.build_geom(data.latitude, data.longitude),
            status=StationStatus.active,
        )
        station = await StationRepository.create(session, station)

        user_station = UserStation(
            id=generate_uuid7(),
            user_id=current_user.id,
            station_id=station.id,
            role=StationUserRole.owner,
        )
        await UserStationRepository.create(session, user_station)

        return StationRead.model_validate(station)

    @staticmethod
    async def get_station(
        session: AsyncSession, station_id: UUID, current_user
    ) -> StationRead:
        station = await StationRepository.find_by_id(session, station_id)
        if station is None:
            raise StationNotFoundError()

        if not _is_admin(current_user):
            has_access = await UserStationRepository.user_has_access(
                session, current_user.id, station_id
            )
            if not has_access:
                raise StationAccessDeniedError()

        return StationRead.model_validate(station)

    @staticmethod
    async def list_stations(
        session: AsyncSession,
        page: int,
        page_size: int,
        current_user,
        zone_id: Optional[UUID] = None,
        status: Optional[StationStatus] = None,
    ) -> StationListResponse:
        offset, limit = paginate(page, page_size)
        if _is_admin(current_user):
            stations, total = await StationRepository.list_all(
                session, offset, limit, zone_id=zone_id, status=status
            )
        else:
            stations, total = await StationRepository.list_for_user(
                session, current_user.id, offset, limit, zone_id=zone_id, status=status
            )
        items = [StationRead.model_validate(s) for s in stations]
        return StationListResponse(**make_paginated_response(items, total, page, limit))

    @staticmethod
    async def update_station(
        session: AsyncSession, station_id: UUID, data: StationUpdate, current_user
    ) -> StationRead:
        station = await StationRepository.find_by_id(session, station_id)
        if station is None:
            raise StationNotFoundError()

        if not _is_admin(current_user):
            role = await UserStationRepository.get_user_role_in_station(
                session, current_user.id, station_id
            )
            if role != StationUserRole.owner:
                raise StationAccessDeniedError()

        update_data = data.model_dump(exclude_unset=True)

        if "zone_id" in update_data:
            zone = await ZoneRepository.find_by_id(session, update_data["zone_id"])
            if zone is None:
                raise ZoneNotFoundError()

        for field, value in update_data.items():
            setattr(station, field, value)

        if "latitude" in update_data or "longitude" in update_data:
            station.geom = StationRepository.build_geom(station.latitude, station.longitude)

        station = await StationRepository.update(session, station)
        return StationRead.model_validate(station)

    @staticmethod
    async def delete_station(
        session: AsyncSession, station_id: UUID, current_user
    ) -> None:
        station = await StationRepository.find_by_id(session, station_id)
        if station is None:
            raise StationNotFoundError()

        if not _is_admin(current_user):
            role = await UserStationRepository.get_user_role_in_station(
                session, current_user.id, station_id
            )
            if role != StationUserRole.owner:
                raise StationAccessDeniedError()

        from modules.devices.repository import DeviceRepository
        await DeviceRepository.unassign_from_station(session, station_id)

        await UserStationRepository.soft_delete_all_for_station(session, station_id)
        await StationRepository.soft_delete(session, station)
