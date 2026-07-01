from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, require_admin
from infrastructure.postgres import get_db_session
from modules.devices.schemas import (
    DeviceAssign,
    DeviceAssignRead,
    DeviceCreate,
    DeviceListResponse,
    DeviceRead,
    DeviceUpdate,
)
from modules.devices.service import DeviceService
from shared.enums import DeviceStatus

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", response_model=DeviceRead, status_code=201)
async def create_device(
    data: DeviceCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(require_admin),
):
    return await DeviceService.create_device(session, data, current_user)


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    status: Optional[DeviceStatus] = Query(None),
    station_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await DeviceService.list_devices(
        session, page, page_size, current_user, status=status, station_id=station_id
    )


@router.get("/{device_id}", response_model=DeviceRead)
async def get_device(
    device_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await DeviceService.get_device(session, device_id, current_user)


@router.patch("/{device_id}", response_model=DeviceRead)
async def update_device(
    device_id: UUID,
    data: DeviceUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(require_admin),
):
    return await DeviceService.update_device(session, device_id, data, current_user)


@router.patch("/{device_id}/assign", response_model=DeviceAssignRead)
async def assign_device(
    device_id: UUID,
    data: DeviceAssign,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(require_admin),
):
    return await DeviceService.assign_device(session, device_id, data, current_user)


@router.patch("/{device_id}/unassign", response_model=DeviceAssignRead)
async def unassign_device(
    device_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(require_admin),
):
    return await DeviceService.unassign_device(session, device_id, current_user)


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(require_admin),
):
    await DeviceService.delete_device(session, device_id, current_user)
