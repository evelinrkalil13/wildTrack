import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, require_admin
from app.main import create_app
from modules.users.schemas import UserListResponse, UserSummary
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
