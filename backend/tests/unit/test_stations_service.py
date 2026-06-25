import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.stations.exceptions import (
    StationAccessDeniedError,
    StationCodeConflictError,
    StationNotFoundError,
)
from modules.stations.schemas import StationCreate, StationRead, StationUpdate
from modules.stations.service import StationService
from modules.zones.exceptions import ZoneNotFoundError
from shared.enums import StationStatus, StationUserRole, UserRole


def _make_station(**kwargs) -> MagicMock:
    from datetime import datetime, timezone

    s = MagicMock()
    s.id = uuid.uuid4()
    s.code = kwargs.get("code", "STA-001")
    s.name = kwargs.get("name", "Test Station")
    s.zone_id = kwargs.get("zone_id", uuid.uuid4())
    s.latitude = kwargs.get("latitude", 4.5)
    s.longitude = kwargs.get("longitude", -74.1)
    s.geom = None
    s.status = kwargs.get("status", StationStatus.active)
    s.deleted_at = None
    now = datetime.now(timezone.utc)
    s.created_at = now
    s.updated_at = now
    return s


def _make_zone() -> MagicMock:
    z = MagicMock()
    z.id = uuid.uuid4()
    z.name = "Test Zone"
    z.deleted_at = None
    return z


def _make_user(role: UserRole = UserRole.researcher) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


@pytest.fixture
def session():
    return AsyncMock()


# ---------------------------------------------------------------------------
# create_station
# ---------------------------------------------------------------------------

class TestCreateStation:
    async def test_creates_station_and_assigns_owner(self, session):
        station_obj = _make_station()
        user = _make_user(UserRole.researcher)
        with (
            patch("modules.stations.service.ZoneRepository.find_by_id", new=AsyncMock(return_value=_make_zone())),
            patch("modules.stations.service.StationRepository.find_by_code", new=AsyncMock(return_value=None)),
            patch("modules.stations.service.StationRepository.create", new=AsyncMock(return_value=station_obj)),
            patch("modules.stations.service.StationRepository.build_geom", return_value=None),
            patch("modules.stations.service.UserStationRepository.create", new=AsyncMock()) as mock_us_create,
        ):
            data = StationCreate(code="STA-001", name="Test Station", zone_id=uuid.uuid4(), latitude=4.5, longitude=-74.1)
            result = await StationService.create_station(session, data, user)
        assert isinstance(result, StationRead)
        assert result.code == station_obj.code
        mock_us_create.assert_called_once()

    async def test_raises_zone_not_found(self, session):
        user = _make_user()
        with patch("modules.stations.service.ZoneRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(ZoneNotFoundError):
                await StationService.create_station(
                    session,
                    StationCreate(code="STA-001", name="X Station", zone_id=uuid.uuid4(), latitude=4.5, longitude=-74.1),
                    user,
                )

    async def test_raises_code_conflict(self, session):
        user = _make_user()
        with (
            patch("modules.stations.service.ZoneRepository.find_by_id", new=AsyncMock(return_value=_make_zone())),
            patch("modules.stations.service.StationRepository.find_by_code", new=AsyncMock(return_value=_make_station())),
        ):
            with pytest.raises(StationCodeConflictError):
                await StationService.create_station(
                    session,
                    StationCreate(code="STA-001", name="X Station", zone_id=uuid.uuid4(), latitude=4.5, longitude=-74.1),
                    user,
                )


# ---------------------------------------------------------------------------
# get_station
# ---------------------------------------------------------------------------

class TestGetStation:
    async def test_admin_can_get_any_station(self, session):
        station_obj = _make_station()
        user = _make_user(UserRole.admin)
        with patch("modules.stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station_obj)):
            result = await StationService.get_station(session, station_obj.id, user)
        assert isinstance(result, StationRead)

    async def test_member_can_get_station(self, session):
        station_obj = _make_station()
        user = _make_user(UserRole.researcher)
        with (
            patch("modules.stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station_obj)),
            patch("modules.stations.service.UserStationRepository.user_has_access", new=AsyncMock(return_value=True)),
        ):
            result = await StationService.get_station(session, station_obj.id, user)
        assert isinstance(result, StationRead)

    async def test_non_member_raises_access_denied(self, session):
        station_obj = _make_station()
        user = _make_user(UserRole.researcher)
        with (
            patch("modules.stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station_obj)),
            patch("modules.stations.service.UserStationRepository.user_has_access", new=AsyncMock(return_value=False)),
        ):
            with pytest.raises(StationAccessDeniedError):
                await StationService.get_station(session, station_obj.id, user)

    async def test_raises_not_found(self, session):
        user = _make_user()
        with patch("modules.stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(StationNotFoundError):
                await StationService.get_station(session, uuid.uuid4(), user)


# ---------------------------------------------------------------------------
# list_stations
# ---------------------------------------------------------------------------

class TestListStations:
    async def test_admin_calls_list_all(self, session):
        stations = [_make_station() for _ in range(3)]
        admin = _make_user(UserRole.admin)
        with patch(
            "modules.stations.service.StationRepository.list_all",
            new=AsyncMock(return_value=(stations, 3)),
        ) as mock_all:
            result = await StationService.list_stations(session, 1, 20, admin)
        mock_all.assert_called_once()
        assert result.total == 3

    async def test_non_admin_calls_list_for_user(self, session):
        stations = [_make_station()]
        user = _make_user(UserRole.researcher)
        with patch(
            "modules.stations.service.StationRepository.list_for_user",
            new=AsyncMock(return_value=(stations, 1)),
        ) as mock_user:
            result = await StationService.list_stations(session, 1, 20, user)
        mock_user.assert_called_once()
        assert result.total == 1

    async def test_zone_id_filter_passed_through(self, session):
        zone_id = uuid.uuid4()
        admin = _make_user(UserRole.admin)
        with patch(
            "modules.stations.service.StationRepository.list_all",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_all:
            await StationService.list_stations(session, 1, 20, admin, zone_id=zone_id)
        _, kwargs = mock_all.call_args
        assert kwargs.get("zone_id") == zone_id


# ---------------------------------------------------------------------------
# update_station
# ---------------------------------------------------------------------------

class TestUpdateStation:
    async def test_admin_can_update(self, session):
        station_obj = _make_station()
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station_obj)),
            patch("modules.stations.service.StationRepository.update", new=AsyncMock(return_value=station_obj)),
        ):
            result = await StationService.update_station(session, station_obj.id, StationUpdate(name="New Name"), admin)
        assert isinstance(result, StationRead)

    async def test_owner_can_update(self, session):
        station_obj = _make_station()
        user = _make_user(UserRole.researcher)
        with (
            patch("modules.stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station_obj)),
            patch("modules.stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.stations.service.StationRepository.update", new=AsyncMock(return_value=station_obj)),
        ):
            result = await StationService.update_station(session, station_obj.id, StationUpdate(name="New Name"), user)
        assert isinstance(result, StationRead)

    async def test_non_owner_raises_access_denied(self, session):
        station_obj = _make_station()
        user = _make_user(UserRole.researcher)
        with (
            patch("modules.stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station_obj)),
            patch("modules.stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.researcher)),
        ):
            with pytest.raises(StationAccessDeniedError):
                await StationService.update_station(session, station_obj.id, StationUpdate(name="X Station"), user)

    async def test_update_zone_id_validates_zone(self, session):
        station_obj = _make_station()
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station_obj)),
            patch("modules.stations.service.ZoneRepository.find_by_id", new=AsyncMock(return_value=None)),
        ):
            with pytest.raises(ZoneNotFoundError):
                await StationService.update_station(session, station_obj.id, StationUpdate(zone_id=uuid.uuid4()), admin)

    async def test_raises_not_found(self, session):
        admin = _make_user(UserRole.admin)
        with patch("modules.stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(StationNotFoundError):
                await StationService.update_station(session, uuid.uuid4(), StationUpdate(name="X Station"), admin)


# ---------------------------------------------------------------------------
# delete_station
# ---------------------------------------------------------------------------

class TestDeleteStation:
    async def test_admin_can_delete(self, session):
        station_obj = _make_station()
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station_obj)),
            patch("modules.stations.service.UserStationRepository.soft_delete_all_for_station", new=AsyncMock()),
            patch("modules.stations.service.StationRepository.soft_delete", new=AsyncMock()),
        ):
            await StationService.delete_station(session, station_obj.id, admin)

    async def test_owner_can_delete(self, session):
        station_obj = _make_station()
        user = _make_user(UserRole.researcher)
        with (
            patch("modules.stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station_obj)),
            patch("modules.stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.stations.service.UserStationRepository.soft_delete_all_for_station", new=AsyncMock()),
            patch("modules.stations.service.StationRepository.soft_delete", new=AsyncMock()),
        ):
            await StationService.delete_station(session, station_obj.id, user)

    async def test_non_owner_raises_access_denied(self, session):
        station_obj = _make_station()
        user = _make_user(UserRole.researcher)
        with (
            patch("modules.stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station_obj)),
            patch("modules.stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.field_operator)),
        ):
            with pytest.raises(StationAccessDeniedError):
                await StationService.delete_station(session, station_obj.id, user)

    async def test_raises_not_found(self, session):
        admin = _make_user(UserRole.admin)
        with patch("modules.stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(StationNotFoundError):
                await StationService.delete_station(session, uuid.uuid4(), admin)
