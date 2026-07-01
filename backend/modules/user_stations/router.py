from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from infrastructure.postgres import get_db_session
from modules.user_stations.schemas import (
    MemberAssign,
    MemberListResponse,
    MemberRead,
    MemberUpdate,
)
from modules.user_stations.service import MemberService

router = APIRouter(prefix="/stations/{station_id}/members", tags=["members"])


@router.post("", response_model=MemberRead, status_code=201)
async def assign_member(
    station_id: UUID,
    data: MemberAssign,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await MemberService.assign_member(session, station_id, data, current_user)


@router.get("", response_model=MemberListResponse)
async def list_members(
    station_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await MemberService.list_members(session, station_id, page, page_size, current_user)


@router.patch("/{us_id}", response_model=MemberRead)
async def update_member_role(
    station_id: UUID,
    us_id: UUID,
    data: MemberUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await MemberService.update_member_role(session, station_id, us_id, data, current_user)


@router.delete("/{us_id}", status_code=204)
async def remove_member(
    station_id: UUID,
    us_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    await MemberService.remove_member(session, station_id, us_id, current_user)
