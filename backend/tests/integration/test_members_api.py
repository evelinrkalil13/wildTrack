import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import create_app
from modules.stations.exceptions import StationNotFoundError
from modules.user_stations.exceptions import (
    AlreadyMemberError,
    CannotAssignOwnerError,
    CannotChangeOwnerRoleError,
    CannotRemoveOwnerError,
    MemberAccessDeniedError,
    MemberNotFoundError,
)
from modules.user_stations.schemas import MemberListResponse, MemberRead
from shared.enums import StationUserRole, UserRole


def _make_user(role: UserRole) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


def _make_member_read(**kwargs) -> MemberRead:
    now = datetime.now(timezone.utc)
    return MemberRead(
        id=kwargs.get("id", uuid.uuid4()),
        station_id=kwargs.get("station_id", uuid.uuid4()),
        user_id=kwargs.get("user_id", uuid.uuid4()),
        user_name=kwargs.get("user_name", "Test User"),
        user_email=kwargs.get("user_email", "test@example.com"),
        role=kwargs.get("role", StationUserRole.researcher),
        created_at=kwargs.get("created_at", now),
    )


def _make_auth_client(role: UserRole = UserRole.researcher) -> TestClient:
    app = create_app()
    fake_user = _make_user(role)
    app.dependency_overrides[get_current_user] = lambda: fake_user
    return TestClient(app, raise_server_exceptions=False)


def _make_no_auth_client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


STATION_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# POST /stations/{station_id}/members
# ---------------------------------------------------------------------------

class TestAssignMember:
    def test_assigns_member_returns_201(self):
        member = _make_member_read(station_id=STATION_ID)
        client = _make_auth_client(UserRole.admin)
        with patch("modules.user_stations.router.MemberService.assign_member", new=AsyncMock(return_value=member)):
            r = client.post(
                f"/api/v1/stations/{STATION_ID}/members",
                json={"user_id": str(uuid.uuid4()), "role": "researcher"},
            )
        assert r.status_code == 201
        assert r.json()["role"] == "researcher"

    def test_cannot_assign_owner_role_returns_422(self):
        client = _make_auth_client(UserRole.admin)
        r = client.post(
            f"/api/v1/stations/{STATION_ID}/members",
            json={"user_id": str(uuid.uuid4()), "role": "owner"},
        )
        assert r.status_code == 422

    def test_already_member_returns_409(self):
        client = _make_auth_client(UserRole.admin)
        with patch("modules.user_stations.router.MemberService.assign_member", new=AsyncMock(side_effect=AlreadyMemberError())):
            r = client.post(
                f"/api/v1/stations/{STATION_ID}/members",
                json={"user_id": str(uuid.uuid4()), "role": "researcher"},
            )
        assert r.status_code == 409
        assert r.json()["error"] == "ALREADY_MEMBER"

    def test_station_not_found_returns_404(self):
        client = _make_auth_client(UserRole.admin)
        with patch("modules.user_stations.router.MemberService.assign_member", new=AsyncMock(side_effect=StationNotFoundError())):
            r = client.post(
                f"/api/v1/stations/{STATION_ID}/members",
                json={"user_id": str(uuid.uuid4()), "role": "researcher"},
            )
        assert r.status_code == 404

    def test_non_owner_returns_403(self):
        client = _make_auth_client(UserRole.researcher)
        with patch("modules.user_stations.router.MemberService.assign_member", new=AsyncMock(side_effect=MemberAccessDeniedError())):
            r = client.post(
                f"/api/v1/stations/{STATION_ID}/members",
                json={"user_id": str(uuid.uuid4()), "role": "researcher"},
            )
        assert r.status_code == 403

    def test_unauthenticated_returns_401(self):
        client = _make_no_auth_client()
        r = client.post(
            f"/api/v1/stations/{STATION_ID}/members",
            json={"user_id": str(uuid.uuid4()), "role": "researcher"},
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /stations/{station_id}/members
# ---------------------------------------------------------------------------

class TestListMembers:
    def test_returns_200_with_members(self):
        members = [_make_member_read(), _make_member_read()]
        response = MemberListResponse(total=2, page=1, page_size=20, pages=1, items=members)
        client = _make_auth_client()
        with patch("modules.user_stations.router.MemberService.list_members", new=AsyncMock(return_value=response)):
            r = client.get(f"/api/v1/stations/{STATION_ID}/members")
        assert r.status_code == 200
        assert r.json()["total"] == 2

    def test_non_member_returns_403(self):
        client = _make_auth_client()
        with patch("modules.user_stations.router.MemberService.list_members", new=AsyncMock(side_effect=MemberAccessDeniedError())):
            r = client.get(f"/api/v1/stations/{STATION_ID}/members")
        assert r.status_code == 403

    def test_unauthenticated_returns_401(self):
        client = _make_no_auth_client()
        r = client.get(f"/api/v1/stations/{STATION_ID}/members")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /stations/{station_id}/members/{us_id}
# ---------------------------------------------------------------------------

class TestUpdateMemberRole:
    def test_updates_role_returns_200(self):
        member = _make_member_read(role=StationUserRole.field_operator)
        client = _make_auth_client(UserRole.admin)
        with patch("modules.user_stations.router.MemberService.update_member_role", new=AsyncMock(return_value=member)):
            r = client.patch(
                f"/api/v1/stations/{STATION_ID}/members/{uuid.uuid4()}",
                json={"role": "field_operator"},
            )
        assert r.status_code == 200
        assert r.json()["role"] == "field_operator"

    def test_cannot_set_owner_role_returns_422(self):
        client = _make_auth_client(UserRole.admin)
        r = client.patch(
            f"/api/v1/stations/{STATION_ID}/members/{uuid.uuid4()}",
            json={"role": "owner"},
        )
        assert r.status_code == 422

    def test_cannot_change_owner_role_returns_400(self):
        client = _make_auth_client(UserRole.admin)
        with patch("modules.user_stations.router.MemberService.update_member_role", new=AsyncMock(side_effect=CannotChangeOwnerRoleError())):
            r = client.patch(
                f"/api/v1/stations/{STATION_ID}/members/{uuid.uuid4()}",
                json={"role": "researcher"},
            )
        assert r.status_code == 400
        assert r.json()["error"] == "CANNOT_CHANGE_OWNER"

    def test_member_not_found_returns_404(self):
        client = _make_auth_client(UserRole.admin)
        with patch("modules.user_stations.router.MemberService.update_member_role", new=AsyncMock(side_effect=MemberNotFoundError())):
            r = client.patch(
                f"/api/v1/stations/{STATION_ID}/members/{uuid.uuid4()}",
                json={"role": "researcher"},
            )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /stations/{station_id}/members/{us_id}
# ---------------------------------------------------------------------------

class TestRemoveMember:
    def test_removes_member_returns_204(self):
        client = _make_auth_client(UserRole.admin)
        with patch("modules.user_stations.router.MemberService.remove_member", new=AsyncMock()):
            r = client.delete(f"/api/v1/stations/{STATION_ID}/members/{uuid.uuid4()}")
        assert r.status_code == 204

    def test_cannot_remove_owner_returns_400(self):
        client = _make_auth_client(UserRole.admin)
        with patch("modules.user_stations.router.MemberService.remove_member", new=AsyncMock(side_effect=CannotRemoveOwnerError())):
            r = client.delete(f"/api/v1/stations/{STATION_ID}/members/{uuid.uuid4()}")
        assert r.status_code == 400
        assert r.json()["error"] == "CANNOT_REMOVE_OWNER"

    def test_member_not_found_returns_404(self):
        client = _make_auth_client(UserRole.admin)
        with patch("modules.user_stations.router.MemberService.remove_member", new=AsyncMock(side_effect=MemberNotFoundError())):
            r = client.delete(f"/api/v1/stations/{STATION_ID}/members/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_non_owner_returns_403(self):
        client = _make_auth_client(UserRole.researcher)
        with patch("modules.user_stations.router.MemberService.remove_member", new=AsyncMock(side_effect=MemberAccessDeniedError())):
            r = client.delete(f"/api/v1/stations/{STATION_ID}/members/{uuid.uuid4()}")
        assert r.status_code == 403
