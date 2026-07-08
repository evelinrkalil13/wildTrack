from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, require_admin, require_researcher_or_above
from infrastructure.postgres import get_db_session
from modules.foods.schemas import FoodCreate, FoodListResponse, FoodRead, FoodUpdate
from modules.foods.service import FoodService
from modules.station_foods.schemas import FoodStationListResponse
from modules.station_foods.service import StationFoodService

router = APIRouter(prefix="/foods", tags=["foods"])


@router.post("", response_model=FoodRead, status_code=201)
async def create_food(
    data: FoodCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(require_researcher_or_above),
):
    return await FoodService.create_food(session, data, current_user)


@router.get("", response_model=FoodListResponse)
async def list_foods(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await FoodService.list_foods(session, page, page_size, current_user)


@router.get("/{food_id}", response_model=FoodRead)
async def get_food(
    food_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await FoodService.get_food(session, food_id, current_user)


@router.patch("/{food_id}", response_model=FoodRead)
async def update_food(
    food_id: UUID,
    data: FoodUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(require_researcher_or_above),
):
    return await FoodService.update_food(session, food_id, data, current_user)


@router.get("/{food_id}/stations", response_model=FoodStationListResponse)
async def get_food_stations(
    food_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await StationFoodService.get_food_stations(session, food_id, current_user)


@router.delete("/{food_id}", status_code=204)
async def delete_food(
    food_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(require_admin),
):
    await FoodService.delete_food(session, food_id, current_user)
