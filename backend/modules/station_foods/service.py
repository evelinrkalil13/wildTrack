from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from modules.foods.exceptions import FoodNotFoundError
from modules.foods.repository import FoodRepository
from modules.station_foods.exceptions import (
    CannotRemoveActiveFoodError,
    FoodAlreadyAssociatedError,
    StationFoodAccessDeniedError,
    StationFoodNotFoundError,
)
from modules.station_foods.models import StationFood
from modules.station_foods.repository import StationFoodRepository
from modules.station_foods.schemas import (
    FoodStationListResponse,
    FoodStationRead,
    StationFoodAdd,
    StationFoodListResponse,
    StationFoodRead,
)
from modules.stations.exceptions import StationNotFoundError
from modules.stations.repository import StationRepository
from modules.user_stations.repository import UserStationRepository
from shared.enums import StationUserRole, UserRole
from shared.pagination import make_paginated_response, paginate
from shared.uuid7 import generate_uuid7


def _is_admin(user) -> bool:
    role_val = user.role.value if hasattr(user.role, "value") else user.role
    return role_val == UserRole.admin.value


def _sf_to_read(sf: StationFood, food_name: str, food_type: str) -> StationFoodRead:
    return StationFoodRead(
        id=sf.id,
        station_id=sf.station_id,
        food_id=sf.food_id,
        food_name=food_name,
        food_type=food_type,
        active=sf.active,
        created_at=sf.created_at,
        updated_at=sf.updated_at,
    )


async def _require_station_owner_or_admin(session, station_id: UUID, current_user) -> None:
    station = await StationRepository.find_by_id(session, station_id)
    if station is None:
        raise StationNotFoundError()
    if not _is_admin(current_user):
        role = await UserStationRepository.get_user_role_in_station(
            session, current_user.id, station_id
        )
        if role != StationUserRole.owner:
            raise StationFoodAccessDeniedError()


async def _require_station_member_or_admin(session, station_id: UUID, current_user) -> None:
    station = await StationRepository.find_by_id(session, station_id)
    if station is None:
        raise StationNotFoundError()
    if not _is_admin(current_user):
        has_access = await UserStationRepository.user_has_access(
            session, current_user.id, station_id
        )
        if not has_access:
            raise StationFoodAccessDeniedError()


class StationFoodService:
    @staticmethod
    async def add_food(
        session: AsyncSession, station_id: UUID, data: StationFoodAdd, current_user
    ) -> StationFoodRead:
        await _require_station_owner_or_admin(session, station_id, current_user)

        food = await FoodRepository.find_by_id(session, data.food_id)
        if food is None:
            raise FoodNotFoundError()

        existing = await StationFoodRepository.find_by_station_and_food(
            session, station_id, data.food_id
        )
        if existing is not None:
            raise FoodAlreadyAssociatedError()

        if data.active:
            current_active = await StationFoodRepository.find_active_for_station(
                session, station_id
            )
            if current_active is not None:
                await StationFoodRepository.deactivate(session, current_active)

        sf = StationFood(
            id=generate_uuid7(),
            station_id=station_id,
            food_id=data.food_id,
            active=data.active,
        )
        sf = await StationFoodRepository.create(session, sf)
        return _sf_to_read(sf, food.name, food.type)

    @staticmethod
    async def list_station_foods(
        session: AsyncSession,
        station_id: UUID,
        page: int,
        page_size: int,
        current_user,
    ) -> StationFoodListResponse:
        await _require_station_member_or_admin(session, station_id, current_user)

        offset, limit = paginate(page, page_size)
        rows, total = await StationFoodRepository.list_for_station_with_food(
            session, station_id, offset, limit
        )
        items = [_sf_to_read(sf, food_name, food_type) for sf, food_name, food_type in rows]
        return StationFoodListResponse(**make_paginated_response(items, total, page, limit))

    @staticmethod
    async def activate_station_food(
        session: AsyncSession, station_id: UUID, sf_id: UUID, current_user
    ) -> StationFoodRead:
        await _require_station_owner_or_admin(session, station_id, current_user)

        row = await StationFoodRepository.find_by_id_in_station_with_food(
            session, sf_id, station_id
        )
        if row is None:
            raise StationFoodNotFoundError()

        sf, food_name, food_type = row

        current_active = await StationFoodRepository.find_active_for_station(
            session, station_id
        )
        if current_active is not None and current_active.id != sf.id:
            await StationFoodRepository.deactivate(session, current_active)

        sf.active = True
        sf = await StationFoodRepository.update(session, sf)
        return _sf_to_read(sf, food_name, food_type)

    @staticmethod
    async def deactivate_station_food(
        session: AsyncSession, station_id: UUID, sf_id: UUID, current_user
    ) -> StationFoodRead:
        await _require_station_owner_or_admin(session, station_id, current_user)

        row = await StationFoodRepository.find_by_id_in_station_with_food(
            session, sf_id, station_id
        )
        if row is None:
            raise StationFoodNotFoundError()

        sf, food_name, food_type = row
        sf.active = False
        sf = await StationFoodRepository.update(session, sf)
        return _sf_to_read(sf, food_name, food_type)

    @staticmethod
    async def get_food_stations(
        session: AsyncSession, food_id: UUID, current_user
    ) -> FoodStationListResponse:
        food = await FoodRepository.find_by_id(session, food_id)
        if food is None:
            raise FoodNotFoundError()

        rows = await StationFoodRepository.list_stations_by_food(session, food_id)
        items = [
            FoodStationRead(
                station_id=station_id,
                station_code=code,
                station_name=name,
                active=active,
                created_at=created_at,
            )
            for station_id, code, name, active, created_at in rows
        ]
        return FoodStationListResponse(total=len(items), items=items)

    @staticmethod
    async def remove_station_food(
        session: AsyncSession, station_id: UUID, sf_id: UUID, current_user
    ) -> None:
        await _require_station_owner_or_admin(session, station_id, current_user)

        sf = await StationFoodRepository.find_by_id_in_station(session, sf_id, station_id)
        if sf is None:
            raise StationFoodNotFoundError()

        if sf.active:
            raise CannotRemoveActiveFoodError()

        await StationFoodRepository.hard_delete(session, sf)
