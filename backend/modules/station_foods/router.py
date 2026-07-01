from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from infrastructure.postgres import get_db_session
from modules.station_foods.schemas import (
    StationFoodAdd,
    StationFoodListResponse,
    StationFoodRead,
)
from modules.station_foods.service import StationFoodService

router = APIRouter(prefix="/stations/{station_id}/foods", tags=["station-foods"])


@router.post("", response_model=StationFoodRead, status_code=201)
async def add_food_to_station(
    station_id: UUID,
    data: StationFoodAdd,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await StationFoodService.add_food(session, station_id, data, current_user)


@router.get("", response_model=StationFoodListResponse)
async def list_station_foods(
    station_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await StationFoodService.list_station_foods(
        session, station_id, page, page_size, current_user
    )


@router.patch("/{sf_id}/activate", response_model=StationFoodRead)
async def activate_station_food(
    station_id: UUID,
    sf_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await StationFoodService.activate_station_food(
        session, station_id, sf_id, current_user
    )


@router.patch("/{sf_id}/deactivate", response_model=StationFoodRead)
async def deactivate_station_food(
    station_id: UUID,
    sf_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await StationFoodService.deactivate_station_food(
        session, station_id, sf_id, current_user
    )


@router.delete("/{sf_id}", status_code=204)
async def remove_food_from_station(
    station_id: UUID,
    sf_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    await StationFoodService.remove_station_food(session, station_id, sf_id, current_user)
