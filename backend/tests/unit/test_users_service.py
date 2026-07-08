import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.users.schemas import UserListResponse, UserSummary
from modules.users.service import UserService
from shared.enums import UserRole


def _make_user(**kwargs) -> MagicMock:
    u = MagicMock()
    u.id = kwargs.get("id", uuid.uuid4())
    u.name = kwargs.get("name", "Ada Lovelace")
    u.email = kwargs.get("email", "ada@example.com")
    u.role = kwargs.get("role", UserRole.researcher)
    u.deleted_at = None
    return u


def _make_admin() -> MagicMock:
    return _make_user(role=UserRole.admin)


@pytest.fixture
def session():
    return AsyncMock()


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------

class TestListUsers:
    async def test_returns_paginated_list(self, session):
        users = [_make_user(), _make_user()]
        admin = _make_admin()
        with patch(
            "modules.users.service.UserRepository.list_all",
            new=AsyncMock(return_value=(users, 2)),
        ):
            result = await UserService.list_users(session, 1, 20, admin)
        assert isinstance(result, UserListResponse)
        assert result.total == 2
        assert len(result.items) == 2
        assert all(isinstance(i, UserSummary) for i in result.items)

    async def test_returns_empty_when_no_users(self, session):
        admin = _make_admin()
        with patch(
            "modules.users.service.UserRepository.list_all",
            new=AsyncMock(return_value=([], 0)),
        ):
            result = await UserService.list_users(session, 1, 20, admin)
        assert result.total == 0
        assert result.items == []

    async def test_passes_search_to_repository(self, session):
        admin = _make_admin()
        with patch(
            "modules.users.service.UserRepository.list_all",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_list:
            await UserService.list_users(session, 1, 20, admin, search="ada")
        _, kwargs = mock_list.call_args
        assert kwargs.get("search") == "ada"

    async def test_response_items_contain_no_password_hash(self, session):
        user = _make_user()
        admin = _make_admin()
        with patch(
            "modules.users.service.UserRepository.list_all",
            new=AsyncMock(return_value=([user], 1)),
        ):
            result = await UserService.list_users(session, 1, 20, admin)
        item = result.items[0]
        assert not hasattr(item, "password_hash")
        assert hasattr(item, "id")
        assert hasattr(item, "name")
        assert hasattr(item, "email")
        assert hasattr(item, "role")
