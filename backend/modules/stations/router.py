from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, require_researcher_or_above
from infrastructure.postgres import get_db_session
from modules.stations.schemas import StationCreate, StationListResponse, StationRead, StationUpdate
from modules.stations.service import StationService
from modules.users.models import User
from shared.enums import StationStatus

router = APIRouter(prefix="/stations", tags=["stations"])


@router.post("", response_model=StationRead, status_code=status.HTTP_201_CREATED)
async def create_station(
    data: StationCreate,
    current_user: User = Depends(require_researcher_or_above),
    session: AsyncSession = Depends(get_db_session),
) -> StationRead:
    return await StationService.create_station(session, data, current_user)


@router.get("", response_model=StationListResponse, status_code=status.HTTP_200_OK)
async def list_stations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    zone_id: Optional[UUID] = Query(None, description="Filter by zone"),
    status: Optional[StationStatus] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StationListResponse:
    return await StationService.list_stations(
        session, page, page_size, current_user, zone_id=zone_id, status=status
    )


@router.get("/{station_id}", response_model=StationRead, status_code=status.HTTP_200_OK)
async def get_station(
    station_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StationRead:
    return await StationService.get_station(session, station_id, current_user)


@router.patch("/{station_id}", response_model=StationRead, status_code=status.HTTP_200_OK)
async def update_station(
    station_id: UUID,
    data: StationUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StationRead:
    return await StationService.update_station(session, station_id, data, current_user)


@router.delete("/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_station(
    station_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await StationService.delete_station(session, station_id, current_user)
