import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import create_app
from modules.auth.exceptions import EmailAlreadyExistsError, InvalidCredentialsError
from modules.auth.schemas import TokenResponse
from modules.users.schemas import UserSummary
from shared.enums import UserRole


def _make_fake_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Test User"
    user.email = "test@example.com"
    user.role = UserRole.researcher
    user.is_active = True
    user.document = "12345"
    user.deleted_at = None
    user.created_at = datetime(2026, 1, 1, 12, 0, 0)
    user.updated_at = datetime(2026, 1, 1, 12, 0, 0)
    return user


@pytest.fixture
def client():
    return TestClient(create_app(), raise_server_exceptions=False)


@pytest.fixture
def authed_client():
    app = create_app()
    fake_user = _make_fake_user()
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _register_payload(**overrides):
    return {
        "name": "Test User",
        "document": "12345",
        "email": "test@example.com",
        "password": "SecurePass1",
        **overrides,
    }


def test_register_returns_201(client):
    fake_user = _make_fake_user()
    with patch("modules.auth.router.AuthService.register", new=AsyncMock(return_value=fake_user)):
        response = client.post("/api/v1/auth/register", json=_register_payload())
    assert response.status_code == 201


def test_register_returns_409_on_duplicate_email(client):
    with patch(
        "modules.auth.router.AuthService.register",
        new=AsyncMock(side_effect=EmailAlreadyExistsError()),
    ):
        response = client.post("/api/v1/auth/register", json=_register_payload())
    assert response.status_code == 409
    assert response.json()["error"] == "EMAIL_ALREADY_EXISTS"


def test_register_returns_422_on_invalid_payload(client):
    response = client.post("/api/v1/auth/register", json={"email": "bad"})
    assert response.status_code == 422


def test_login_returns_200_with_token(client):
    fake_user = _make_fake_user()
    fake_token = TokenResponse(
        access_token="fake.jwt.token",
        token_type="bearer",
        expires_in=86400,
        user=UserSummary(
            id=fake_user.id,
            name=fake_user.name,
            email=fake_user.email,
            role=fake_user.role,
        ),
    )
    with patch("modules.auth.router.AuthService.login", new=AsyncMock(return_value=fake_token)):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "SecurePass1"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "fake.jwt.token"
    assert body["token_type"] == "bearer"


def test_login_returns_401_on_invalid_credentials(client):
    with patch(
        "modules.auth.router.AuthService.login",
        new=AsyncMock(side_effect=InvalidCredentialsError()),
    ):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
        )
    assert response.status_code == 401
    assert response.json()["error"] == "INVALID_CREDENTIALS"


def test_login_returns_422_on_empty_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": ""},
    )
    assert response.status_code == 422


def test_me_returns_current_user(authed_client):
    response = authed_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "test@example.com"


def test_me_returns_401_without_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "UNAUTHORIZED"
