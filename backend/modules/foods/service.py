from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from modules.foods.exceptions import FoodInUseError, FoodNameConflictError, FoodNotFoundError
from modules.foods.models import Food
from modules.foods.repository import FoodRepository
from modules.foods.schemas import FoodCreate, FoodListResponse, FoodRead, FoodUpdate
from modules.station_foods.repository import StationFoodRepository
from shared.pagination import make_paginated_response, paginate
from shared.uuid7 import generate_uuid7


def _to_read(food: Food) -> FoodRead:
    return FoodRead(
        id=food.id,
        name=food.name,
        type=food.type,
        description=food.description,
        created_at=food.created_at,
        updated_at=food.updated_at,
    )


class FoodService:
    @staticmethod
    async def create_food(
        session: AsyncSession, data: FoodCreate, current_user
    ) -> FoodRead:
        existing = await FoodRepository.find_by_name(session, data.name)
        if existing is not None:
            raise FoodNameConflictError()

        food = Food(
            id=generate_uuid7(),
            name=data.name,
            type=data.type,
            description=data.description,
        )
        food = await FoodRepository.create(session, food)
        return _to_read(food)

    @staticmethod
    async def get_food(
        session: AsyncSession, food_id: UUID, current_user
    ) -> FoodRead:
        food = await FoodRepository.find_by_id(session, food_id)
        if food is None:
            raise FoodNotFoundError()
        return _to_read(food)

    @staticmethod
    async def list_foods(
        session: AsyncSession,
        page: int,
        page_size: int,
        current_user,
    ) -> FoodListResponse:
        offset, limit = paginate(page, page_size)
        foods, total = await FoodRepository.list_all(session, offset, limit)
        items = [_to_read(f) for f in foods]
        return FoodListResponse(**make_paginated_response(items, total, page, limit))

    @staticmethod
    async def update_food(
        session: AsyncSession, food_id: UUID, data: FoodUpdate, current_user
    ) -> FoodRead:
        food = await FoodRepository.find_by_id(session, food_id)
        if food is None:
            raise FoodNotFoundError()

        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data and update_data["name"] != food.name:
            existing = await FoodRepository.find_by_name(session, update_data["name"])
            if existing is not None:
                raise FoodNameConflictError()

        for field, value in update_data.items():
            setattr(food, field, value)

        food = await FoodRepository.update(session, food)
        return _to_read(food)

    @staticmethod
    async def delete_food(
        session: AsyncSession, food_id: UUID, current_user
    ) -> None:
        food = await FoodRepository.find_by_id(session, food_id)
        if food is None:
            raise FoodNotFoundError()

        is_active = await StationFoodRepository.has_active_for_food(session, food_id)
        if is_active:
            raise FoodInUseError()

        await FoodRepository.soft_delete(session, food)
