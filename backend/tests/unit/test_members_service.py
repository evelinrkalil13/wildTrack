import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.stations.exceptions import StationNotFoundError
from modules.user_stations.exceptions import (
    AlreadyMemberError,
    CannotAssignOwnerError,
    CannotChangeOwnerRoleError,
    CannotRemoveOwnerError,
    MemberAccessDeniedError,
    MemberNotFoundError,
)
from modules.user_stations.schemas import MemberAssign, MemberRead, MemberUpdate
from modules.user_stations.service import MemberService
from shared.base_exception import NotFoundError
from shared.enums import StationUserRole, UserRole


def _make_station() -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.deleted_at = None
    return s


def _make_user_record(**kwargs) -> MagicMock:
    u = MagicMock()
    u.id = kwargs.get("id", uuid.uuid4())
    u.name = kwargs.get("name", "Test User")
    u.email = kwargs.get("email", "test@example.com")
    return u


def _make_us(**kwargs) -> MagicMock:
    us = MagicMock()
    us.id = kwargs.get("id", uuid.uuid4())
    us.station_id = kwargs.get("station_id", uuid.uuid4())
    us.user_id = kwargs.get("user_id", uuid.uuid4())
    us.role = kwargs.get("role", StationUserRole.researcher)
    us.deleted_at = None
    now = datetime.now(timezone.utc)
    us.created_at = now
    return us


def _make_caller(role: UserRole = UserRole.admin) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


@pytest.fixture
def session():
    return AsyncMock()


# ---------------------------------------------------------------------------
# assign_member
# ---------------------------------------------------------------------------

class TestAssignMember:
    async def test_assigns_researcher_to_station(self, session):
        station = _make_station()
        target_user = _make_user_record()
        us = _make_us(station_id=station.id, user_id=target_user.id, role=StationUserRole.researcher)
        admin = _make_caller(UserRole.admin)
        with (
            patch("modules.user_stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.user_stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.user_stations.service.UserRepository.find_by_id", new=AsyncMock(return_value=target_user)),
            patch("modules.user_stations.service.UserStationRepository.find_by_user_and_station", new=AsyncMock(return_value=None)),
            patch("modules.user_stations.service.UserStationRepository.create", new=AsyncMock(return_value=us)),
        ):
            result = await MemberService.assign_member(
                session, station.id,
                MemberAssign(user_id=target_user.id, role=StationUserRole.researcher),
                admin,
            )
        assert isinstance(result, MemberRead)
        assert result.role == StationUserRole.researcher

    async def test_raises_cannot_assign_owner(self, session):
        with pytest.raises(Exception):
            MemberAssign(user_id=uuid.uuid4(), role=StationUserRole.owner)

    async def test_raises_already_member(self, session):
        station = _make_station()
        target_user = _make_user_record()
        existing_us = _make_us()
        admin = _make_caller()
        with (
            patch("modules.user_stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.user_stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.user_stations.service.UserRepository.find_by_id", new=AsyncMock(return_value=target_user)),
            patch("modules.user_stations.service.UserStationRepository.find_by_user_and_station", new=AsyncMock(return_value=existing_us)),
        ):
            with pytest.raises(AlreadyMemberError):
                await MemberService.assign_member(
                    session, station.id,
                    MemberAssign(user_id=target_user.id, role=StationUserRole.researcher),
                    admin,
                )

    async def test_raises_station_not_found(self, session):
        admin = _make_caller()
        with patch("modules.user_stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(StationNotFoundError):
                await MemberService.assign_member(
                    session, uuid.uuid4(),
                    MemberAssign(user_id=uuid.uuid4(), role=StationUserRole.researcher),
                    admin,
                )

    async def test_raises_user_not_found(self, session):
        station = _make_station()
        admin = _make_caller()
        with (
            patch("modules.user_stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.user_stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.user_stations.service.UserRepository.find_by_id", new=AsyncMock(return_value=None)),
        ):
            with pytest.raises(NotFoundError):
                await MemberService.assign_member(
                    session, station.id,
                    MemberAssign(user_id=uuid.uuid4(), role=StationUserRole.researcher),
                    admin,
                )

    async def test_non_owner_raises_forbidden(self, session):
        station = _make_station()
        researcher = _make_caller(UserRole.researcher)
        with (
            patch("modules.user_stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.user_stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.researcher)),
        ):
            with pytest.raises(MemberAccessDeniedError):
                await MemberService.assign_member(
                    session, station.id,
                    MemberAssign(user_id=uuid.uuid4(), role=StationUserRole.researcher),
                    researcher,
                )


# ---------------------------------------------------------------------------
# update_member_role
# ---------------------------------------------------------------------------

class TestUpdateMemberRole:
    async def test_updates_researcher_to_field_operator(self, session):
        station = _make_station()
        us = _make_us(role=StationUserRole.researcher)
        target_user = _make_user_record(id=us.user_id)
        us_after = _make_us(role=StationUserRole.field_operator)
        admin = _make_caller()
        with (
            patch("modules.user_stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.user_stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.user_stations.service.UserStationRepository.find_by_id_in_station", new=AsyncMock(return_value=us)),
            patch("modules.user_stations.service.UserRepository.find_by_id", new=AsyncMock(return_value=target_user)),
            patch("modules.user_stations.service.UserStationRepository.update", new=AsyncMock(return_value=us_after)),
        ):
            result = await MemberService.update_member_role(
                session, station.id, us.id,
                MemberUpdate(role=StationUserRole.field_operator),
                admin,
            )
        assert result.role == StationUserRole.field_operator

    async def test_raises_cannot_change_owner_role(self, session):
        station = _make_station()
        us = _make_us(role=StationUserRole.owner)
        admin = _make_caller()
        with (
            patch("modules.user_stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.user_stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.user_stations.service.UserStationRepository.find_by_id_in_station", new=AsyncMock(return_value=us)),
        ):
            with pytest.raises(CannotChangeOwnerRoleError):
                await MemberService.update_member_role(
                    session, station.id, us.id,
                    MemberUpdate(role=StationUserRole.researcher),
                    admin,
                )

    async def test_raises_member_not_found(self, session):
        station = _make_station()
        admin = _make_caller()
        with (
            patch("modules.user_stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.user_stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.user_stations.service.UserStationRepository.find_by_id_in_station", new=AsyncMock(return_value=None)),
        ):
            with pytest.raises(MemberNotFoundError):
                await MemberService.update_member_role(
                    session, station.id, uuid.uuid4(),
                    MemberUpdate(role=StationUserRole.researcher),
                    admin,
                )


# ---------------------------------------------------------------------------
# remove_member
# ---------------------------------------------------------------------------

class TestRemoveMember:
    async def test_removes_researcher(self, session):
        station = _make_station()
        us = _make_us(role=StationUserRole.researcher)
        admin = _make_caller()
        with (
            patch("modules.user_stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.user_stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.user_stations.service.UserStationRepository.find_by_id_in_station", new=AsyncMock(return_value=us)),
            patch("modules.user_stations.service.UserStationRepository.soft_delete_one", new=AsyncMock()),
        ):
            await MemberService.remove_member(session, station.id, us.id, admin)

    async def test_raises_cannot_remove_owner(self, session):
        station = _make_station()
        us = _make_us(role=StationUserRole.owner)
        admin = _make_caller()
        with (
            patch("modules.user_stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.user_stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.user_stations.service.UserStationRepository.find_by_id_in_station", new=AsyncMock(return_value=us)),
        ):
            with pytest.raises(CannotRemoveOwnerError):
                await MemberService.remove_member(session, station.id, us.id, admin)

    async def test_raises_member_not_found(self, session):
        station = _make_station()
        admin = _make_caller()
        with (
            patch("modules.user_stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.user_stations.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.user_stations.service.UserStationRepository.find_by_id_in_station", new=AsyncMock(return_value=None)),
        ):
            with pytest.raises(MemberNotFoundError):
                await MemberService.remove_member(session, station.id, uuid.uuid4(), admin)


# ---------------------------------------------------------------------------
# list_members
# ---------------------------------------------------------------------------

class TestListMembers:
    async def test_returns_paginated_response(self, session):
        station = _make_station()
        user1 = _make_user_record(name="Alice", email="alice@x.com")
        user2 = _make_user_record(name="Bob", email="bob@x.com")
        us1 = _make_us(station_id=station.id, role=StationUserRole.owner)
        us2 = _make_us(station_id=station.id, role=StationUserRole.researcher)
        admin = _make_caller()
        rows = [(us1, "Alice", "alice@x.com"), (us2, "Bob", "bob@x.com")]
        with (
            patch("modules.user_stations.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.user_stations.service.UserStationRepository.user_has_access", new=AsyncMock(return_value=True)),
            patch("modules.user_stations.service.UserStationRepository.list_for_station_with_users", new=AsyncMock(return_value=(rows, 2))),
        ):
            result = await MemberService.list_members(session, station.id, 1, 20, admin)
        assert result.total == 2
        assert result.items[0].user_name == "Alice"
        assert result.items[1].user_name == "Bob"
