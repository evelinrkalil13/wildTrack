from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from infrastructure.postgres import get_db_session
from modules.geoportal.schemas import (
    ActivityItem,
    AnimalHistoryResponse,
    GeoportalAnimalRead,
    GeoportalStationDetail,
    GeoportalStationMapItem,
    GeoportalStatsResponse,
    StationEventsResponse,
)
from modules.geoportal.service import GeoportalService
from modules.users.models import User
from shared.enums import TimeFilter

router = APIRouter(prefix="/geoportal", tags=["geoportal"])


@router.get("/stations", response_model=list[GeoportalStationMapItem])
async def list_geoportal_stations(
    time_filter: TimeFilter = TimeFilter.d7,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> list[GeoportalStationMapItem]:
    return await GeoportalService.list_stations(session, time_filter)


@router.get("/stations/{station_id}", response_model=GeoportalStationDetail)
async def get_geoportal_station_detail(
    station_id: str,
    time_filter: TimeFilter = TimeFilter.d7,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> GeoportalStationDetail:
    detail = await GeoportalService.get_station_detail(session, station_id, time_filter)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found",
        )
    return detail


@router.get("/stations/{station_id}/animals", response_model=list[GeoportalAnimalRead])
async def list_station_animals(
    station_id: str,
    time_filter: TimeFilter = TimeFilter.d7,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> list[GeoportalAnimalRead]:
    return await GeoportalService.list_station_animals(session, station_id, time_filter)


@router.get("/stations/{station_id}/activity", response_model=list[ActivityItem])
async def list_station_activity(
    station_id: str,
    limit: int = Query(20, ge=1, le=50),
    _: User = Depends(get_current_user),
) -> list[ActivityItem]:
    return await GeoportalService.list_station_activity(station_id, limit)


@router.get("/stats", response_model=GeoportalStatsResponse)
async def get_geoportal_stats(
    time_filter: TimeFilter = TimeFilter.d7,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> GeoportalStatsResponse:
    return await GeoportalService.get_global_stats(session, time_filter)


@router.get("/stations/{station_id}/events", response_model=StationEventsResponse)
async def get_station_events(
    station_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    filter: str = Query("all", pattern="^(all|identified|unidentified)$"),
    time_filter: TimeFilter = TimeFilter.d7,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> StationEventsResponse:
    result = await GeoportalService.get_station_events(
        session, station_id, page, page_size, filter, time_filter
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found",
        )
    return result


@router.get("/animals/{animal_id}/history", response_model=AnimalHistoryResponse)
async def get_animal_history(
    animal_id: str,
    time_filter: TimeFilter = TimeFilter.all,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> AnimalHistoryResponse:
    history = await GeoportalService.get_animal_history(session, animal_id, time_filter)
    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found or has no RFID tag",
        )
    return history
