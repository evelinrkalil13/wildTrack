import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.devices.exceptions import (
    DeviceAccessDeniedError,
    DeviceAlreadyAssignedError,
    DeviceNotAssignedError,
    DeviceNotFoundError,
    SerialNumberConflictError,
    StationHasDeviceError,
)
from modules.devices.schemas import DeviceAssign, DeviceCreate, DeviceRead, DeviceUpdate
from modules.devices.service import DeviceService
from modules.stations.exceptions import StationNotFoundError
from shared.enums import DeviceStatus, UserRole


def _make_device(**kwargs) -> MagicMock:
    d = MagicMock()
    d.id = kwargs.get("id", uuid.uuid4())
    d.serial_number = kwargs.get("serial_number", "WT-ESP32-0001")
    d.name = kwargs.get("name", "Feeder Alpha")
    d.mac_address = kwargs.get("mac_address", None)
    d.station_id = kwargs.get("station_id", None)
    d.status = kwargs.get("status", DeviceStatus.unassigned)
    d.firmware_version = kwargs.get("firmware_version", None)
    d.last_seen = kwargs.get("last_seen", None)
    d.deleted_at = None
    now = datetime.now(timezone.utc)
    d.created_at = now
    d.updated_at = now
    return d


def _make_station() -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.code = "STA-001"
    s.deleted_at = None
    return s


def _make_user(role: UserRole = UserRole.researcher) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


@pytest.fixture
def session():
    return AsyncMock()


# ---------------------------------------------------------------------------
# create_device
# ---------------------------------------------------------------------------

class TestCreateDevice:
    async def test_creates_device_with_status_unassigned(self, session):
        device_obj = _make_device()
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.devices.service.DeviceRepository.find_by_serial", new=AsyncMock(return_value=None)),
            patch("modules.devices.service.DeviceRepository.create", new=AsyncMock(return_value=device_obj)),
        ):
            result = await DeviceService.create_device(
                session,
                DeviceCreate(serial_number="WT-ESP32-0001"),
                admin,
            )
        assert isinstance(result, DeviceRead)
        assert result.status == DeviceStatus.unassigned
        assert result.station_id is None
        assert result.station_code is None

    async def test_creates_device_with_mac_address(self, session):
        device_obj = _make_device(mac_address="AA:BB:CC:DD:EE:FF")
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.devices.service.DeviceRepository.find_by_serial", new=AsyncMock(return_value=None)),
            patch("modules.devices.service.DeviceRepository.create", new=AsyncMock(return_value=device_obj)),
        ):
            result = await DeviceService.create_device(
                session,
                DeviceCreate(serial_number="WT-ESP32-0001", mac_address="AA:BB:CC:DD:EE:FF"),
                admin,
            )
        assert result.mac_address == "AA:BB:CC:DD:EE:FF"

    async def test_raises_serial_conflict(self, session):
        admin = _make_user(UserRole.admin)
        with patch(
            "modules.devices.service.DeviceRepository.find_by_serial",
            new=AsyncMock(return_value=_make_device()),
        ):
            with pytest.raises(SerialNumberConflictError):
                await DeviceService.create_device(
                    session,
                    DeviceCreate(serial_number="WT-ESP32-0001"),
                    admin,
                )


# ---------------------------------------------------------------------------
# get_device
# ---------------------------------------------------------------------------

class TestGetDevice:
    async def test_admin_can_get_unassigned_device(self, session):
        device_obj = _make_device(station_id=None, status=DeviceStatus.unassigned)
        admin = _make_user(UserRole.admin)
        with patch(
            "modules.devices.service.DeviceRepository.find_by_id_with_code",
            new=AsyncMock(return_value=(device_obj, None)),
        ):
            result = await DeviceService.get_device(session, device_obj.id, admin)
        assert isinstance(result, DeviceRead)
        assert result.station_code is None

    async def test_admin_can_get_assigned_device(self, session):
        station_id = uuid.uuid4()
        device_obj = _make_device(station_id=station_id, status=DeviceStatus.online)
        admin = _make_user(UserRole.admin)
        with patch(
            "modules.devices.service.DeviceRepository.find_by_id_with_code",
            new=AsyncMock(return_value=(device_obj, "STA-001")),
        ):
            result = await DeviceService.get_device(session, device_obj.id, admin)
        assert result.station_code == "STA-001"

    async def test_non_admin_cannot_get_unassigned_device(self, session):
        device_obj = _make_device(station_id=None, status=DeviceStatus.unassigned)
        user = _make_user(UserRole.researcher)
        with patch(
            "modules.devices.service.DeviceRepository.find_by_id_with_code",
            new=AsyncMock(return_value=(device_obj, None)),
        ):
            with pytest.raises(DeviceAccessDeniedError):
                await DeviceService.get_device(session, device_obj.id, user)

    async def test_member_can_get_assigned_device(self, session):
        station_id = uuid.uuid4()
        device_obj = _make_device(station_id=station_id, status=DeviceStatus.online)
        user = _make_user(UserRole.researcher)
        with (
            patch(
                "modules.devices.service.DeviceRepository.find_by_id_with_code",
                new=AsyncMock(return_value=(device_obj, "STA-001")),
            ),
            patch(
                "modules.devices.service.UserStationRepository.user_has_access",
                new=AsyncMock(return_value=True),
            ),
        ):
            result = await DeviceService.get_device(session, device_obj.id, user)
        assert isinstance(result, DeviceRead)

    async def test_non_member_cannot_get_assigned_device(self, session):
        station_id = uuid.uuid4()
        device_obj = _make_device(station_id=station_id, status=DeviceStatus.online)
        user = _make_user(UserRole.researcher)
        with (
            patch(
                "modules.devices.service.DeviceRepository.find_by_id_with_code",
                new=AsyncMock(return_value=(device_obj, "STA-001")),
            ),
            patch(
                "modules.devices.service.UserStationRepository.user_has_access",
                new=AsyncMock(return_value=False),
            ),
        ):
            with pytest.raises(DeviceAccessDeniedError):
                await DeviceService.get_device(session, device_obj.id, user)

    async def test_raises_not_found(self, session):
        user = _make_user()
        with patch(
            "modules.devices.service.DeviceRepository.find_by_id_with_code",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(DeviceNotFoundError):
                await DeviceService.get_device(session, uuid.uuid4(), user)


# ---------------------------------------------------------------------------
# list_devices
# ---------------------------------------------------------------------------

class TestListDevices:
    async def test_admin_calls_list_all(self, session):
        admin = _make_user(UserRole.admin)
        device = _make_device()
        with patch(
            "modules.devices.service.DeviceRepository.list_all",
            new=AsyncMock(return_value=([(device, None)], 1)),
        ) as mock_all:
            result = await DeviceService.list_devices(session, 1, 20, admin)
        mock_all.assert_called_once()
        assert result.total == 1

    async def test_non_admin_calls_list_for_user(self, session):
        user = _make_user(UserRole.researcher)
        station_id = uuid.uuid4()
        device = _make_device(station_id=station_id, status=DeviceStatus.online)
        with patch(
            "modules.devices.service.DeviceRepository.list_for_user",
            new=AsyncMock(return_value=([(device, "STA-001")], 1)),
        ) as mock_user:
            result = await DeviceService.list_devices(session, 1, 20, user)
        mock_user.assert_called_once()
        assert result.total == 1

    async def test_status_filter_passed_to_list_all(self, session):
        admin = _make_user(UserRole.admin)
        with patch(
            "modules.devices.service.DeviceRepository.list_all",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_all:
            await DeviceService.list_devices(
                session, 1, 20, admin, status=DeviceStatus.online
            )
        _, kwargs = mock_all.call_args
        assert kwargs.get("status") == DeviceStatus.online

    async def test_station_id_filter_passed_to_list_for_user(self, session):
        user = _make_user(UserRole.researcher)
        station_id = uuid.uuid4()
        with patch(
            "modules.devices.service.DeviceRepository.list_for_user",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_user:
            await DeviceService.list_devices(
                session, 1, 20, user, station_id=station_id
            )
        _, kwargs = mock_user.call_args
        assert kwargs.get("station_id") == station_id


# ---------------------------------------------------------------------------
# update_device
# ---------------------------------------------------------------------------

class TestUpdateDevice:
    async def test_admin_can_update_name(self, session):
        device_obj = _make_device(name="Old Name")
        device_obj.name = "New Name"
        admin = _make_user(UserRole.admin)
        with (
            patch(
                "modules.devices.service.DeviceRepository.find_by_id_with_code",
                new=AsyncMock(return_value=(device_obj, None)),
            ),
            patch(
                "modules.devices.service.DeviceRepository.update",
                new=AsyncMock(return_value=device_obj),
            ),
        ):
            result = await DeviceService.update_device(
                session, device_obj.id, DeviceUpdate(name="New Name"), admin
            )
        assert isinstance(result, DeviceRead)

    async def test_raises_not_found(self, session):
        admin = _make_user(UserRole.admin)
        with patch(
            "modules.devices.service.DeviceRepository.find_by_id_with_code",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(DeviceNotFoundError):
                await DeviceService.update_device(
                    session, uuid.uuid4(), DeviceUpdate(name="X"), admin
                )


# ---------------------------------------------------------------------------
# assign_device
# ---------------------------------------------------------------------------

class TestAssignDevice:
    async def test_assigns_device_and_sets_status_online(self, session):
        station_id = uuid.uuid4()
        # before_device starts unassigned; after_device represents the post-update state
        before_device = _make_device(status=DeviceStatus.unassigned, station_id=None)
        after_device = _make_device(id=before_device.id, status=DeviceStatus.online, station_id=station_id)
        station_obj = _make_station()
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.devices.service.DeviceRepository.find_by_id", new=AsyncMock(return_value=before_device)),
            patch("modules.devices.service.StationRepository.find_by_id", new=AsyncMock(return_value=station_obj)),
            patch("modules.devices.service.DeviceRepository.find_active_for_station", new=AsyncMock(return_value=None)),
            patch("modules.devices.service.DeviceRepository.update", new=AsyncMock(return_value=after_device)),
        ):
            result = await DeviceService.assign_device(
                session, before_device.id, DeviceAssign(station_id=station_id), admin
            )
        assert result.status == DeviceStatus.online
        assert result.station_id == station_id

    async def test_raises_if_device_already_assigned(self, session):
        station_id = uuid.uuid4()
        device_obj = _make_device(station_id=station_id, status=DeviceStatus.online)
        admin = _make_user(UserRole.admin)
        with patch(
            "modules.devices.service.DeviceRepository.find_by_id",
            new=AsyncMock(return_value=device_obj),
        ):
            with pytest.raises(DeviceAlreadyAssignedError):
                await DeviceService.assign_device(
                    session, device_obj.id, DeviceAssign(station_id=station_id), admin
                )

    async def test_raises_if_station_not_found(self, session):
        device_obj = _make_device(status=DeviceStatus.unassigned)
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.devices.service.DeviceRepository.find_by_id", new=AsyncMock(return_value=device_obj)),
            patch("modules.devices.service.StationRepository.find_by_id", new=AsyncMock(return_value=None)),
        ):
            with pytest.raises(StationNotFoundError):
                await DeviceService.assign_device(
                    session, device_obj.id, DeviceAssign(station_id=uuid.uuid4()), admin
                )

    async def test_raises_if_station_has_device(self, session):
        station_id = uuid.uuid4()
        device_obj = _make_device(status=DeviceStatus.unassigned)
        station_obj = _make_station()
        existing = _make_device(station_id=station_id, status=DeviceStatus.online)
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.devices.service.DeviceRepository.find_by_id", new=AsyncMock(return_value=device_obj)),
            patch("modules.devices.service.StationRepository.find_by_id", new=AsyncMock(return_value=station_obj)),
            patch("modules.devices.service.DeviceRepository.find_active_for_station", new=AsyncMock(return_value=existing)),
        ):
            with pytest.raises(StationHasDeviceError):
                await DeviceService.assign_device(
                    session, device_obj.id, DeviceAssign(station_id=station_id), admin
                )

    async def test_raises_if_device_not_found(self, session):
        admin = _make_user(UserRole.admin)
        with patch(
            "modules.devices.service.DeviceRepository.find_by_id",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(DeviceNotFoundError):
                await DeviceService.assign_device(
                    session, uuid.uuid4(), DeviceAssign(station_id=uuid.uuid4()), admin
                )


# ---------------------------------------------------------------------------
# unassign_device
# ---------------------------------------------------------------------------

class TestUnassignDevice:
    async def test_unassigns_device_and_sets_status_unassigned(self, session):
        station_id = uuid.uuid4()
        # before_device is assigned; after_device represents the post-update state
        before_device = _make_device(station_id=station_id, status=DeviceStatus.online)
        after_device = _make_device(id=before_device.id, station_id=None, status=DeviceStatus.unassigned)
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.devices.service.DeviceRepository.find_by_id", new=AsyncMock(return_value=before_device)),
            patch("modules.devices.service.DeviceRepository.update", new=AsyncMock(return_value=after_device)),
        ):
            result = await DeviceService.unassign_device(session, before_device.id, admin)
        assert result.status == DeviceStatus.unassigned
        assert result.station_id is None

    async def test_raises_if_device_not_assigned(self, session):
        device_obj = _make_device(station_id=None, status=DeviceStatus.unassigned)
        admin = _make_user(UserRole.admin)
        with patch(
            "modules.devices.service.DeviceRepository.find_by_id",
            new=AsyncMock(return_value=device_obj),
        ):
            with pytest.raises(DeviceNotAssignedError):
                await DeviceService.unassign_device(session, device_obj.id, admin)

    async def test_raises_if_device_not_found(self, session):
        admin = _make_user(UserRole.admin)
        with patch(
            "modules.devices.service.DeviceRepository.find_by_id",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(DeviceNotFoundError):
                await DeviceService.unassign_device(session, uuid.uuid4(), admin)


# ---------------------------------------------------------------------------
# delete_device
# ---------------------------------------------------------------------------

class TestDeleteDevice:
    async def test_deletes_unassigned_device(self, session):
        device_obj = _make_device(status=DeviceStatus.unassigned)
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.devices.service.DeviceRepository.find_by_id", new=AsyncMock(return_value=device_obj)),
            patch("modules.devices.service.DeviceRepository.soft_delete", new=AsyncMock()) as mock_del,
        ):
            await DeviceService.delete_device(session, device_obj.id, admin)
        mock_del.assert_called_once()

    async def test_deletes_assigned_device_after_unassigning(self, session):
        station_id = uuid.uuid4()
        device_obj = _make_device(station_id=station_id, status=DeviceStatus.online)
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.devices.service.DeviceRepository.find_by_id", new=AsyncMock(return_value=device_obj)),
            patch("modules.devices.service.DeviceRepository.soft_delete", new=AsyncMock()) as mock_del,
        ):
            await DeviceService.delete_device(session, device_obj.id, admin)
        mock_del.assert_called_once()
        # station_id and status were mutated before soft_delete
        assert device_obj.station_id is None
        assert device_obj.status == DeviceStatus.unassigned

    async def test_raises_if_device_not_found(self, session):
        admin = _make_user(UserRole.admin)
        with patch(
            "modules.devices.service.DeviceRepository.find_by_id",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(DeviceNotFoundError):
                await DeviceService.delete_device(session, uuid.uuid4(), admin)
