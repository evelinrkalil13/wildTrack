import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.users.exceptions import (
    CannotChangeOwnRoleError,
    InvalidCurrentPasswordError,
    UserNotFoundError,
)
from modules.users.schemas import (
    PasswordChange,
    UserListResponse,
    UserProfileUpdate,
    UserRead,
    UserRoleUpdate,
    UserSummary,
)
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


def _make_full_user(**kwargs) -> MagicMock:
    u = _make_user(**kwargs)
    u.document = None
    u.is_active = True
    now = datetime.now(timezone.utc)
    u.created_at = now
    u.updated_at = now
    u.password_hash = "hashed_password"
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


# ---------------------------------------------------------------------------
# update_profile
# ---------------------------------------------------------------------------

class TestUpdateProfile:
    async def test_sets_new_name_on_user(self, session):
        user = _make_full_user()
        data = UserProfileUpdate(name="New Name")
        with patch("modules.users.service.UserRepository.save", new=AsyncMock(return_value=user)):
            await UserService.update_profile(session, user, data)
        assert user.name == "New Name"

    async def test_returns_user_read(self, session):
        user = _make_full_user()
        data = UserProfileUpdate(name="New Name")
        with patch("modules.users.service.UserRepository.save", new=AsyncMock(return_value=user)):
            result = await UserService.update_profile(session, user, data)
        assert isinstance(result, UserRead)
        assert result.id == user.id

    async def test_updated_at_is_set(self, session):
        user = _make_full_user()
        data = UserProfileUpdate(name="New Name")
        with patch("modules.users.service.UserRepository.save", new=AsyncMock(return_value=user)):
            await UserService.update_profile(session, user, data)
        assert user.updated_at is not None


# ---------------------------------------------------------------------------
# change_password
# ---------------------------------------------------------------------------

class TestChangePassword:
    async def test_updates_password_hash_on_success(self, session):
        user = _make_full_user()
        data = PasswordChange(current_password="OldPass1", new_password="NewPass1")
        with patch("modules.users.service.verify_password", return_value=True), \
             patch("modules.users.service.hash_password", return_value="new_hashed"), \
             patch("modules.users.service.UserRepository.save", new=AsyncMock(return_value=user)):
            await UserService.change_password(session, user, data)
        assert user.password_hash == "new_hashed"

    async def test_raises_when_current_password_is_wrong(self, session):
        user = _make_full_user()
        data = PasswordChange(current_password="WrongPass1", new_password="NewPass1")
        with patch("modules.users.service.verify_password", return_value=False):
            with pytest.raises(InvalidCurrentPasswordError):
                await UserService.change_password(session, user, data)

    async def test_does_not_save_when_password_is_wrong(self, session):
        user = _make_full_user()
        data = PasswordChange(current_password="WrongPass1", new_password="NewPass1")
        with patch("modules.users.service.verify_password", return_value=False), \
             patch("modules.users.service.UserRepository.save", new=AsyncMock()) as mock_save:
            with pytest.raises(InvalidCurrentPasswordError):
                await UserService.change_password(session, user, data)
        mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# update_role
# ---------------------------------------------------------------------------

class TestUpdateRole:
    async def test_updates_role_for_other_user(self, session):
        admin = _make_full_user(role=UserRole.admin)
        target = _make_full_user()
        data = UserRoleUpdate(role=UserRole.admin)
        with patch("modules.users.service.UserRepository.find_by_id", new=AsyncMock(return_value=target)), \
             patch("modules.users.service.UserRepository.save", new=AsyncMock(return_value=target)):
            result = await UserService.update_role(session, target.id, data, admin)
        assert target.role == UserRole.admin
        assert isinstance(result, UserSummary)

    async def test_raises_when_target_not_found(self, session):
        admin = _make_full_user(role=UserRole.admin)
        data = UserRoleUpdate(role=UserRole.admin)
        with patch("modules.users.service.UserRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(UserNotFoundError):
                await UserService.update_role(session, uuid.uuid4(), data, admin)

    async def test_raises_when_changing_own_role(self, session):
        admin = _make_full_user(role=UserRole.admin)
        data = UserRoleUpdate(role=UserRole.researcher)
        with pytest.raises(CannotChangeOwnRoleError):
            await UserService.update_role(session, admin.id, data, admin)
