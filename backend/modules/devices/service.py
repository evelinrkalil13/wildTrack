from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from modules.devices.exceptions import (
    DeviceAccessDeniedError,
    DeviceAlreadyAssignedError,
    DeviceNotAssignedError,
    DeviceNotFoundError,
    SerialNumberConflictError,
    StationHasDeviceError,
)
from modules.devices.models import Device
from modules.devices.repository import DeviceRepository
from modules.devices.schemas import (
    DeviceAssign,
    DeviceAssignRead,
    DeviceCreate,
    DeviceListResponse,
    DeviceRead,
    DeviceUpdate,
)
from modules.stations.exceptions import StationNotFoundError
from modules.stations.repository import StationRepository
from modules.user_stations.repository import UserStationRepository
from shared.enums import DeviceStatus, UserRole
from shared.pagination import make_paginated_response, paginate
from shared.uuid7 import generate_uuid7


def _is_admin(user) -> bool:
    role_val = user.role.value if hasattr(user.role, "value") else user.role
    return role_val == UserRole.admin.value


def _device_to_read(device: Device, station_code: Optional[str]) -> DeviceRead:
    return DeviceRead(
        id=device.id,
        serial_number=device.serial_number,
        name=device.name,
        mac_address=device.mac_address,
        station_id=device.station_id,
        station_code=station_code,
        status=device.status,
        firmware_version=device.firmware_version,
        last_seen=device.last_seen,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


class DeviceService:
    @staticmethod
    async def create_device(
        session: AsyncSession, data: DeviceCreate, current_user
    ) -> DeviceRead:
        existing = await DeviceRepository.find_by_serial(session, data.serial_number)
        if existing is not None:
            raise SerialNumberConflictError()

        device = Device(
            id=generate_uuid7(),
            serial_number=data.serial_number,
            name=data.name,
            mac_address=data.mac_address,
            station_id=None,
            status=DeviceStatus.unassigned,
        )
        device = await DeviceRepository.create(session, device)
        return _device_to_read(device, station_code=None)

    @staticmethod
    async def get_device(
        session: AsyncSession, device_id: UUID, current_user
    ) -> DeviceRead:
        row = await DeviceRepository.find_by_id_with_code(session, device_id)
        if row is None:
            raise DeviceNotFoundError()

        device, station_code = row

        if not _is_admin(current_user):
            if device.station_id is None:
                raise DeviceAccessDeniedError()
            has_access = await UserStationRepository.user_has_access(
                session, current_user.id, device.station_id
            )
            if not has_access:
                raise DeviceAccessDeniedError()

        return _device_to_read(device, station_code)

    @staticmethod
    async def list_devices(
        session: AsyncSession,
        page: int,
        page_size: int,
        current_user,
        status: Optional[DeviceStatus] = None,
        station_id: Optional[UUID] = None,
    ) -> DeviceListResponse:
        offset, limit = paginate(page, page_size)
        if _is_admin(current_user):
            rows, total = await DeviceRepository.list_all(
                session, offset, limit, status=status, station_id=station_id
            )
        else:
            rows, total = await DeviceRepository.list_for_user(
                session, current_user.id, offset, limit, status=status, station_id=station_id
            )

        items = [_device_to_read(device, code) for device, code in rows]
        return DeviceListResponse(**make_paginated_response(items, total, page, limit))

    @staticmethod
    async def update_device(
        session: AsyncSession, device_id: UUID, data: DeviceUpdate, current_user
    ) -> DeviceRead:
        row = await DeviceRepository.find_by_id_with_code(session, device_id)
        if row is None:
            raise DeviceNotFoundError()

        device, station_code = row

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(device, field, value)

        device = await DeviceRepository.update(session, device)
        return _device_to_read(device, station_code)

    @staticmethod
    async def assign_device(
        session: AsyncSession, device_id: UUID, data: DeviceAssign, current_user
    ) -> DeviceAssignRead:
        device = await DeviceRepository.find_by_id(session, device_id)
        if device is None:
            raise DeviceNotFoundError()

        if device.status != DeviceStatus.unassigned:
            raise DeviceAlreadyAssignedError()

        station = await StationRepository.find_by_id(session, data.station_id)
        if station is None:
            raise StationNotFoundError()

        existing = await DeviceRepository.find_active_for_station(session, data.station_id)
        if existing is not None:
            raise StationHasDeviceError()

        device.station_id = data.station_id
        device.status = DeviceStatus.online
        device = await DeviceRepository.update(session, device)
        return DeviceAssignRead.model_validate(device)

    @staticmethod
    async def unassign_device(
        session: AsyncSession, device_id: UUID, current_user
    ) -> DeviceAssignRead:
        device = await DeviceRepository.find_by_id(session, device_id)
        if device is None:
            raise DeviceNotFoundError()

        if device.status == DeviceStatus.unassigned:
            raise DeviceNotAssignedError()

        device.station_id = None
        device.status = DeviceStatus.unassigned
        device = await DeviceRepository.update(session, device)
        return DeviceAssignRead.model_validate(device)

    @staticmethod
    async def delete_device(
        session: AsyncSession, device_id: UUID, current_user
    ) -> None:
        device = await DeviceRepository.find_by_id(session, device_id)
        if device is None:
            raise DeviceNotFoundError()

        if device.status != DeviceStatus.unassigned:
            device.station_id = None
            device.status = DeviceStatus.unassigned

        await DeviceRepository.soft_delete(session, device)
