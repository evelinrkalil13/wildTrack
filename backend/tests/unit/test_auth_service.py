import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.auth.exceptions import AccountInactiveError, EmailAlreadyExistsError, InvalidCredentialsError
from modules.auth.schemas import LoginRequest, RegisterRequest
from modules.auth.service import AuthService
from shared.enums import UserRole
from shared.security import hash_password


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def register_data():
    return RegisterRequest(
        name="Jane Doe",
        document="12345",
        email="jane@example.com",
        password="SecurePass1",
    )


@pytest.fixture
def fake_active_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Jane Doe"
    user.email = "jane@example.com"
    user.role = UserRole.researcher
    user.is_active = True
    user.password_hash = hash_password("SecurePass1")
    return user


async def test_register_returns_user(mock_session, register_data):
    fake_user = MagicMock()
    with (
        patch("modules.auth.service.UserRepository.find_by_email", new=AsyncMock(return_value=None)),
        patch("modules.auth.service.UserRepository.create", new=AsyncMock(return_value=fake_user)),
    ):
        result = await AuthService.register(mock_session, register_data)
    assert result is fake_user


async def test_register_raises_on_duplicate_email(mock_session, register_data, fake_active_user):
    with patch(
        "modules.auth.service.UserRepository.find_by_email",
        new=AsyncMock(return_value=fake_active_user),
    ):
        with pytest.raises(EmailAlreadyExistsError):
            await AuthService.register(mock_session, register_data)


async def test_login_returns_token_response(mock_session, fake_active_user):
    data = LoginRequest(email="jane@example.com", password="SecurePass1")
    with patch(
        "modules.auth.service.UserRepository.find_by_email",
        new=AsyncMock(return_value=fake_active_user),
    ):
        result = await AuthService.login(mock_session, data)
    assert result.access_token
    assert result.token_type == "bearer"
    assert result.user.email == "jane@example.com"


async def test_login_raises_on_wrong_password(mock_session, fake_active_user):
    data = LoginRequest(email="jane@example.com", password="WrongPass99")
    with patch(
        "modules.auth.service.UserRepository.find_by_email",
        new=AsyncMock(return_value=fake_active_user),
    ):
        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(mock_session, data)


async def test_login_raises_on_missing_user(mock_session):
    data = LoginRequest(email="ghost@example.com", password="SecurePass1")
    with patch(
        "modules.auth.service.UserRepository.find_by_email",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(mock_session, data)


async def test_login_raises_on_inactive_account(mock_session, fake_active_user):
    fake_active_user.is_active = False
    data = LoginRequest(email="jane@example.com", password="SecurePass1")
    with patch(
        "modules.auth.service.UserRepository.find_by_email",
        new=AsyncMock(return_value=fake_active_user),
    ):
        with pytest.raises(AccountInactiveError):
            await AuthService.login(mock_session, data)
