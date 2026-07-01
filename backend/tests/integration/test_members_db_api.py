"""
Real-database integration tests for the Station Members module.

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


async def _get_user_id(email: str) -> str:
    settings = get_settings()
    conn = await asyncpg.connect(
        host=settings.postgres_host,
        port=int(settings.postgres_port),
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )
    try:
        row = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
        return str(row["id"])
    finally:
        await conn.close()


async def _get_owner_us_id(station_id: str) -> str:
    settings = get_settings()
    conn = await asyncpg.connect(
        host=settings.postgres_host,
        port=int(settings.postgres_port),
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )
    try:
        row = await conn.fetchrow(
            "SELECT id FROM user_stations WHERE station_id = $1 AND role = 'owner' AND deleted_at IS NULL",
            uuid.UUID(station_id),
        )
        return str(row["id"])
    finally:
        await conn.close()


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
    email = f"mem-db-{time.time_ns()}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "document": "66666", "email": email, "password": "SecurePass1"},
    )
    assert r.status_code == 201
    if role == "admin":
        asyncio.run(_promote_to_admin(email))
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass1"})
    assert login.status_code == 200
    return login.json()["access_token"], email


def _create_station_for(client: TestClient, token: str) -> str:
    r_zone = client.post(
        "/api/v1/zones",
        json={"name": f"Zone {uuid.uuid4().hex[:6]}", "city": "X", "country": "CO",
              "latitude": 4.0, "longitude": -74.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    zone_id = r_zone.json()["id"]
    r_sta = client.post(
        "/api/v1/stations",
        json={"code": f"MB{uuid.uuid4().hex[:8].upper()}", "name": "Station",
              "zone_id": zone_id, "latitude": 4.0, "longitude": -74.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_sta.status_code == 201
    return r_sta.json()["id"]


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(), raise_server_exceptions=True) as c:
        yield c


class TestMembersCrudAgainstRealDb:
    def test_assign_member_returns_201(self, client):
        owner_token, _ = _register_and_get_token(client)
        station_id = _create_station_for(client, owner_token)
        _, target_email = _register_and_get_token(client)
        target_user_id = asyncio.run(_get_user_id(target_email))

        r = client.post(
            f"/api/v1/stations/{station_id}/members",
            json={"user_id": target_user_id, "role": "researcher"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 201
        assert r.json()["role"] == "researcher"
        assert r.json()["user_email"] == target_email

    def test_cannot_assign_owner_role_returns_422(self, client):
        owner_token, _ = _register_and_get_token(client)
        station_id = _create_station_for(client, owner_token)
        r = client.post(
            f"/api/v1/stations/{station_id}/members",
            json={"user_id": str(uuid.uuid4()), "role": "owner"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 422

    def test_duplicate_member_returns_409(self, client):
        owner_token, _ = _register_and_get_token(client)
        station_id = _create_station_for(client, owner_token)
        _, target_email = _register_and_get_token(client)
        target_user_id = asyncio.run(_get_user_id(target_email))

        client.post(
            f"/api/v1/stations/{station_id}/members",
            json={"user_id": target_user_id, "role": "researcher"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        r2 = client.post(
            f"/api/v1/stations/{station_id}/members",
            json={"user_id": target_user_id, "role": "field_operator"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r2.status_code == 409
        assert r2.json()["error"] == "ALREADY_MEMBER"

    def test_list_members_includes_owner(self, client):
        owner_token, _ = _register_and_get_token(client)
        station_id = _create_station_for(client, owner_token)
        r = client.get(
            f"/api/v1/stations/{station_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 200
        roles = [m["role"] for m in r.json()["items"]]
        assert "owner" in roles

    def test_update_member_role(self, client):
        owner_token, _ = _register_and_get_token(client)
        station_id = _create_station_for(client, owner_token)
        _, target_email = _register_and_get_token(client)
        target_user_id = asyncio.run(_get_user_id(target_email))

        us = client.post(
            f"/api/v1/stations/{station_id}/members",
            json={"user_id": target_user_id, "role": "researcher"},
            headers={"Authorization": f"Bearer {owner_token}"},
        ).json()

        r = client.patch(
            f"/api/v1/stations/{station_id}/members/{us['id']}",
            json={"role": "field_operator"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 200
        assert r.json()["role"] == "field_operator"

    def test_cannot_remove_owner(self, client):
        owner_token, _ = _register_and_get_token(client)
        station_id = _create_station_for(client, owner_token)
        owner_us_id = asyncio.run(_get_owner_us_id(station_id))

        r = client.delete(
            f"/api/v1/stations/{station_id}/members/{owner_us_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 400
        assert r.json()["error"] == "CANNOT_REMOVE_OWNER"

    def test_remove_member_returns_204(self, client):
        owner_token, _ = _register_and_get_token(client)
        station_id = _create_station_for(client, owner_token)
        _, target_email = _register_and_get_token(client)
        target_user_id = asyncio.run(_get_user_id(target_email))

        us = client.post(
            f"/api/v1/stations/{station_id}/members",
            json={"user_id": target_user_id, "role": "field_operator"},
            headers={"Authorization": f"Bearer {owner_token}"},
        ).json()

        r = client.delete(
            f"/api/v1/stations/{station_id}/members/{us['id']}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 204

    def test_non_member_cannot_list_members(self, client):
        owner_token, _ = _register_and_get_token(client)
        station_id = _create_station_for(client, owner_token)
        outsider_token, _ = _register_and_get_token(client)

        r = client.get(
            f"/api/v1/stations/{station_id}/members",
            headers={"Authorization": f"Bearer {outsider_token}"},
        )
        assert r.status_code == 403
