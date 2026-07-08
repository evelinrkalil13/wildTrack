import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, require_admin
from app.main import create_app
from modules.users.exceptions import (
    CannotChangeOwnRoleError,
    InvalidCurrentPasswordError,
    UserNotFoundError,
)
from modules.users.schemas import UserListResponse, UserRead, UserSummary
from shared.enums import UserRole


def _make_user(role: UserRole = UserRole.researcher) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


def _make_summary(**kwargs) -> UserSummary:
    return UserSummary(
        id=kwargs.get("id", uuid.uuid4()),
        name=kwargs.get("name", "Ada Lovelace"),
        email=kwargs.get("email", "ada@example.com"),
        role=kwargs.get("role", UserRole.researcher),
    )


def _make_admin_client() -> TestClient:
    app = create_app()
    fake = _make_user(UserRole.admin)
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[require_admin] = lambda: fake
    return TestClient(app, raise_server_exceptions=False)


def _make_researcher_client() -> TestClient:
    app = create_app()
    fake = _make_user(UserRole.researcher)
    app.dependency_overrides[get_current_user] = lambda: fake
    return TestClient(app, raise_server_exceptions=False)


def _make_no_auth_client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


def _make_user_read(**kwargs) -> UserRead:
    now = datetime.now(timezone.utc)
    return UserRead(
        id=kwargs.get("id", uuid.uuid4()),
        name=kwargs.get("name", "Ada Lovelace"),
        document=None,
        email=kwargs.get("email", "ada@example.com"),
        role=kwargs.get("role", UserRole.researcher),
        is_active=True,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------

class TestListUsers:
    def test_admin_gets_200_with_items(self):
        items = [_make_summary(), _make_summary()]
        response = UserListResponse(total=2, page=1, page_size=20, pages=1, items=items)
        client = _make_admin_client()
        with patch("modules.users.router.UserService.list_users", new=AsyncMock(return_value=response)):
            r = client.get("/api/v1/users")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert "password_hash" not in data["items"][0]

    def test_admin_gets_empty_list(self):
        response = UserListResponse(total=0, page=1, page_size=20, pages=0, items=[])
        client = _make_admin_client()
        with patch("modules.users.router.UserService.list_users", new=AsyncMock(return_value=response)):
            r = client.get("/api/v1/users")
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_search_param_forwarded(self):
        response = UserListResponse(total=0, page=1, page_size=20, pages=0, items=[])
        client = _make_admin_client()
        with patch(
            "modules.users.router.UserService.list_users", new=AsyncMock(return_value=response)
        ) as mock_svc:
            client.get("/api/v1/users?search=ada")
        _, kwargs = mock_svc.call_args
        assert kwargs.get("search") == "ada"

    def test_non_admin_gets_403(self):
        client = _make_researcher_client()
        r = client.get("/api/v1/users")
        assert r.status_code == 403

    def test_unauthenticated_gets_401(self):
        client = _make_no_auth_client()
        r = client.get("/api/v1/users")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /users/me
# ---------------------------------------------------------------------------

class TestUpdateProfile:
    def test_returns_200_with_updated_name(self):
        read = _make_user_read(name="New Name")
        client = _make_researcher_client()
        with patch("modules.users.router.UserService.update_profile", new=AsyncMock(return_value=read)):
            r = client.patch("/api/v1/users/me", json={"name": "New Name"})
        assert r.status_code == 200
        assert r.json()["name"] == "New Name"

    def test_response_contains_no_password_hash(self):
        read = _make_user_read(name="New Name")
        client = _make_researcher_client()
        with patch("modules.users.router.UserService.update_profile", new=AsyncMock(return_value=read)):
            r = client.patch("/api/v1/users/me", json={"name": "New Name"})
        assert "password_hash" not in r.json()

    def test_rejects_too_short_name(self):
        client = _make_researcher_client()
        r = client.patch("/api/v1/users/me", json={"name": "A"})
        assert r.status_code == 422

    def test_unauthenticated_gets_401(self):
        r = _make_no_auth_client().patch("/api/v1/users/me", json={"name": "New Name"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /users/me/password
# ---------------------------------------------------------------------------

class TestChangePassword:
    def test_returns_204_on_success(self):
        client = _make_researcher_client()
        with patch("modules.users.router.UserService.change_password", new=AsyncMock(return_value=None)):
            r = client.patch(
                "/api/v1/users/me/password",
                json={"current_password": "OldPass1", "new_password": "NewPass1"},
            )
        assert r.status_code == 204

    def test_returns_400_when_current_password_wrong(self):
        client = _make_researcher_client()
        with patch(
            "modules.users.router.UserService.change_password",
            new=AsyncMock(side_effect=InvalidCurrentPasswordError()),
        ):
            r = client.patch(
                "/api/v1/users/me/password",
                json={"current_password": "WrongPass1", "new_password": "NewPass1"},
            )
        assert r.status_code == 400
        assert r.json()["error"] == "INVALID_CURRENT_PASSWORD"

    def test_rejects_weak_new_password(self):
        client = _make_researcher_client()
        r = client.patch(
            "/api/v1/users/me/password",
            json={"current_password": "OldPass1", "new_password": "weak"},
        )
        assert r.status_code == 422

    def test_unauthenticated_gets_401(self):
        r = _make_no_auth_client().patch(
            "/api/v1/users/me/password",
            json={"current_password": "OldPass1", "new_password": "NewPass1"},
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /users/{user_id}/role
# ---------------------------------------------------------------------------

class TestUpdateUserRole:
    def test_admin_updates_role_successfully(self):
        other_id = uuid.uuid4()
        summary = _make_summary(id=other_id, role=UserRole.admin)
        client = _make_admin_client()
        with patch("modules.users.router.UserService.update_role", new=AsyncMock(return_value=summary)):
            r = client.patch(f"/api/v1/users/{other_id}/role", json={"role": "admin"})
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_returns_403_when_changing_own_role(self):
        admin_user = _make_user(UserRole.admin)
        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[require_admin] = lambda: admin_user
        client = TestClient(app, raise_server_exceptions=False)
        with patch(
            "modules.users.router.UserService.update_role",
            new=AsyncMock(side_effect=CannotChangeOwnRoleError()),
        ):
            r = client.patch(f"/api/v1/users/{admin_user.id}/role", json={"role": "researcher"})
        assert r.status_code == 403
        assert r.json()["error"] == "CANNOT_CHANGE_OWN_ROLE"

    def test_returns_404_when_user_not_found(self):
        client = _make_admin_client()
        with patch(
            "modules.users.router.UserService.update_role",
            new=AsyncMock(side_effect=UserNotFoundError()),
        ):
            r = client.patch(f"/api/v1/users/{uuid.uuid4()}/role", json={"role": "admin"})
        assert r.status_code == 404

    def test_non_admin_gets_403(self):
        r = _make_researcher_client().patch(f"/api/v1/users/{uuid.uuid4()}/role", json={"role": "admin"})
        assert r.status_code == 403

    def test_unauthenticated_gets_401(self):
        r = _make_no_auth_client().patch(f"/api/v1/users/{uuid.uuid4()}/role", json={"role": "admin"})
        assert r.status_code == 401
