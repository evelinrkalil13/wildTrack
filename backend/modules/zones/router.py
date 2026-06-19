from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, require_admin, require_researcher_or_above
from infrastructure.postgres import get_db_session
from modules.zones.schemas import ZoneCreate, ZoneListResponse, ZoneRead, ZoneUpdate
from modules.zones.service import ZoneService
from modules.users.models import User

router = APIRouter(prefix="/zones", tags=["zones"])


@router.get("", response_model=ZoneListResponse, status_code=status.HTTP_200_OK)
async def list_zones(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    country: Optional[str] = Query(None, description="Filter by country name"),
    _current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ZoneListResponse:
    return await ZoneService.list_zones(session, page, page_size, country=country)


@router.get("/{zone_id}", response_model=ZoneRead, status_code=status.HTTP_200_OK)
async def get_zone(
    zone_id: UUID,
    _current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ZoneRead:
    return await ZoneService.get_zone(session, zone_id)


@router.post("", response_model=ZoneRead, status_code=status.HTTP_201_CREATED)
async def create_zone(
    data: ZoneCreate,
    _current_user: User = Depends(require_researcher_or_above),
    session: AsyncSession = Depends(get_db_session),
) -> ZoneRead:
    return await ZoneService.create_zone(session, data)


@router.patch("/{zone_id}", response_model=ZoneRead, status_code=status.HTTP_200_OK)
async def update_zone(
    zone_id: UUID,
    data: ZoneUpdate,
    _current_user: User = Depends(require_researcher_or_above),
    session: AsyncSession = Depends(get_db_session),
) -> ZoneRead:
    return await ZoneService.update_zone(session, zone_id, data)


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    zone_id: UUID,
    _current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await ZoneService.delete_zone(session, zone_id)
