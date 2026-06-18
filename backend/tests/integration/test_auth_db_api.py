import os
import time

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION_TESTS") != "1",
    reason="Set RUN_DB_INTEGRATION_TESTS=1 and run PostgreSQL migrations to enable DB tests.",
)


def test_register_login_me_with_real_database():
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        email = f"auth-db-{time.time_ns()}@example.com"
        register_payload = {
            "name": "DB Integration User",
            "document": "12345",
            "email": email,
            "password": "SecurePass1",
        }

        register_response = client.post("/api/v1/auth/register", json=register_payload)

        assert register_response.status_code == 201
        registered = register_response.json()
        assert registered["email"] == email
        assert registered["document"] == "12345"
        assert registered["role"] == "researcher"
        assert registered["is_active"] is True

        duplicate_response = client.post("/api/v1/auth/register", json=register_payload)

        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["error"] == "EMAIL_ALREADY_EXISTS"

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "SecurePass1"},
        )

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert me_response.status_code == 200
        assert me_response.json()["email"] == email
