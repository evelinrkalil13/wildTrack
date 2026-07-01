"""
Real-database integration tests for the Foods module.

Requires a running PostgreSQL + PostGIS container with migrations at head.
Skipped unless RUN_DB_INTEGRATION_TESTS=1 is set.
"""
import asyncio
import os
import time
import uuid

import asyncpg
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from shared.config import get_settings

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION_TESTS") != "1",
    reason="Set RUN_DB_INTEGRATION_TESTS=1 and run PostgreSQL migrations to enable DB tests.",
)


async def _promote_to_admin(email: str) -> None:
    settings = get_settings()
    conn = await asyncpg.connect(
        host=settings.postgres_host,
        port=int(settings.postgres_port),
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )
    try:
        await conn.execute("UPDATE users SET role = 'admin' WHERE email = $1", email)
    finally:
        await conn.close()


def _register_and_get_token(
    client: TestClient, role: str = "researcher"
) -> tuple[str, str]:
    email = f"foods-db-{time.time_ns()}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "document": "88888", "email": email, "password": "SecurePass1"},
    )
    assert r.status_code == 201
    if role == "admin":
        asyncio.run(_promote_to_admin(email))
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass1"})
    assert login.status_code == 200
    return login.json()["access_token"], email


def _create_food(client: TestClient, token: str, **overrides) -> dict:
    name = overrides.get("name", f"Food-{uuid.uuid4().hex[:8]}")
    payload = {"name": name, "type": "seeds", **overrides}
    r = client.post(
        "/api/v1/foods",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, f"food create failed: {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(), raise_server_exceptions=True) as c:
        yield c


class TestFoodsCrudAgainstRealDb:
    def test_researcher_creates_food_returns_201(self, client):
        token, _ = _register_and_get_token(client, role="researcher")
        food = _create_food(client, token)
        assert "id" in food
        assert food["type"] == "seeds"

    def test_duplicate_name_returns_409(self, client):
        token, _ = _register_and_get_token(client, role="researcher")
        name = f"UniqueFood-{uuid.uuid4().hex[:8]}"
        _create_food(client, token, name=name)
        r = client.post(
            "/api/v1/foods",
            json={"name": name, "type": "pellets"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 409
        assert r.json()["error"] == "FOOD_NAME_EXISTS"

    def test_field_operator_cannot_create_returns_403(self, client):
        email = f"fo-{time.time_ns()}@example.com"
        client.post(
            "/api/v1/auth/register",
            json={"name": "FO", "document": "77771", "email": email, "password": "SecurePass1"},
        )
        login = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass1"})
        fo_token = login.json()["access_token"]
        r = client.post(
            "/api/v1/foods",
            json={"name": "FO Food", "type": "seeds"},
            headers={"Authorization": f"Bearer {fo_token}"},
        )
        assert r.status_code == 403

    def test_get_food_returns_200(self, client):
        token, _ = _register_and_get_token(client)
        food = _create_food(client, token)
        r = client.get(
            f"/api/v1/foods/{food['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["id"] == food["id"]

    def test_unknown_food_returns_404(self, client):
        token, _ = _register_and_get_token(client)
        r = client.get(
            f"/api/v1/foods/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404

    def test_update_food_name(self, client):
        token, _ = _register_and_get_token(client)
        food = _create_food(client, token)
        new_name = f"Updated-{uuid.uuid4().hex[:8]}"
        r = client.patch(
            f"/api/v1/foods/{food['id']}",
            json={"name": new_name},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["name"] == new_name

    def test_admin_deletes_food_not_in_use(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        food = _create_food(client, admin_token)
        r = client.delete(
            f"/api/v1/foods/{food['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 204
        r2 = client.get(
            f"/api/v1/foods/{food['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r2.status_code == 404

    def test_researcher_cannot_delete_returns_403(self, client):
        token, _ = _register_and_get_token(client, role="researcher")
        food = _create_food(client, token)
        r = client.delete(
            f"/api/v1/foods/{food['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403
