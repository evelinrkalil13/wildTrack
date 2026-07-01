from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.devices.models import Device
from shared.enums import DeviceStatus


class DeviceRepository:
    @staticmethod
    async def find_by_id(session: AsyncSession, device_id: UUID) -> Optional[Device]:
        result = await session.execute(
            select(Device).where(Device.id == device_id, Device.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_id_with_code(session: AsyncSession, device_id: UUID) -> Optional[tuple]:
        from modules.stations.models import Station

        result = await session.execute(
            select(Device, Station.code)
            .outerjoin(Station, Device.station_id == Station.id)
            .where(Device.id == device_id, Device.deleted_at.is_(None))
        )
        return result.one_or_none()

    @staticmethod
    async def find_by_serial(session: AsyncSession, serial_number: str) -> Optional[Device]:
        result = await session.execute(
            select(Device).where(
                Device.serial_number == serial_number,
                Device.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_active_for_station(
        session: AsyncSession, station_id: UUID
    ) -> Optional[Device]:
        result = await session.execute(
            select(Device).where(
                Device.station_id == station_id,
                Device.status != DeviceStatus.unassigned,
                Device.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(
        session: AsyncSession,
        offset: int,
        limit: int,
        status: Optional[DeviceStatus] = None,
        station_id: Optional[UUID] = None,
    ) -> tuple[list[tuple], int]:
        from modules.stations.models import Station

        conditions = [Device.deleted_at.is_(None)]
        if status is not None:
            conditions.append(Device.status == status)
        if station_id is not None:
            conditions.append(Device.station_id == station_id)

        base = select(Device).where(*conditions)
        count_result = await session.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        result = await session.execute(
            select(Device, Station.code)
            .outerjoin(Station, Device.station_id == Station.id)
            .where(*conditions)
            .offset(offset)
            .limit(limit)
        )
        return list(result.all()), total

    @staticmethod
    async def list_for_user(
        session: AsyncSession,
        user_id: UUID,
        offset: int,
        limit: int,
        status: Optional[DeviceStatus] = None,
        station_id: Optional[UUID] = None,
    ) -> tuple[list[tuple], int]:
        from modules.stations.models import Station
        from modules.user_stations.models import UserStation

        conditions = [
            Device.deleted_at.is_(None),
            Device.station_id.isnot(None),
            select(UserStation.id)
            .where(
                UserStation.station_id == Device.station_id,
                UserStation.user_id == user_id,
                UserStation.deleted_at.is_(None),
            )
            .exists(),
        ]
        if status is not None:
            conditions.append(Device.status == status)
        if station_id is not None:
            conditions.append(Device.station_id == station_id)

        base = select(Device).where(*conditions)
        count_result = await session.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        result = await session.execute(
            select(Device, Station.code)
            .outerjoin(Station, Device.station_id == Station.id)
            .where(*conditions)
            .offset(offset)
            .limit(limit)
        )
        return list(result.all()), total

    @staticmethod
    async def create(session: AsyncSession, device: Device) -> Device:
        session.add(device)
        await session.commit()
        await session.refresh(device)
        return device

    @staticmethod
    async def update(session: AsyncSession, device: Device) -> Device:
        await session.commit()
        await session.refresh(device)
        return device

    @staticmethod
    async def soft_delete(session: AsyncSession, device: Device) -> None:
        device.deleted_at = datetime.now(timezone.utc)
        await session.commit()

    @staticmethod
    async def find_by_id_with_station(
        session: AsyncSession, device_id: UUID
    ) -> Optional[tuple]:
        from modules.stations.models import Station

        result = await session.execute(
            select(Device, Station.code, Station.zone_id)
            .outerjoin(Station, Device.station_id == Station.id)
            .where(Device.id == device_id, Device.deleted_at.is_(None))
        )
        return result.one_or_none()

    @staticmethod
    async def update_last_seen(session: AsyncSession, device_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        await session.execute(
            update(Device)
            .where(Device.id == device_id, Device.deleted_at.is_(None))
            .values(last_seen=now, updated_at=now)
        )
        await session.commit()

    @staticmethod
    async def set_online(session: AsyncSession, device_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        await session.execute(
            update(Device)
            .where(Device.id == device_id, Device.deleted_at.is_(None))
            .values(status=DeviceStatus.online, last_seen=now, updated_at=now)
        )
        await session.commit()

    @staticmethod
    async def set_offline(session: AsyncSession, device_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        await session.execute(
            update(Device)
            .where(Device.id == device_id, Device.deleted_at.is_(None))
            .values(status=DeviceStatus.offline, updated_at=now)
        )
        await session.commit()

    @staticmethod
    async def unassign_from_station(session: AsyncSession, station_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        await session.execute(
            update(Device)
            .where(
                Device.station_id == station_id,
                Device.deleted_at.is_(None),
            )
            .values(station_id=None, status=DeviceStatus.unassigned, updated_at=now)
        )
        await session.commit()
