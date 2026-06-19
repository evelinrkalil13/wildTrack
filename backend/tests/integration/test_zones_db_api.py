"""
Real-database integration tests for the Zones module.

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


def _zone_payload(suffix: str = "", **overrides) -> dict:
    return {
        "name": f"DBZone {suffix}",
        "municipality": "Test Municipality",
        "city": "Test City",
        "country": f"DBCountry{suffix}",
        "altitude": 1800.0,
        "latitude": 4.5,
        "longitude": -74.1,
        **overrides,
    }


async def _promote_to_admin(email: str) -> None:
    """Promote a user to admin using a direct asyncpg connection (avoids engine loop conflict)."""
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


def _register_and_get_token(client: TestClient, role: str = "researcher") -> str:
    email = f"zones-db-{time.time_ns()}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "document": "11111", "email": email, "password": "SecurePass1"},
    )
    assert r.status_code == 201, f"register failed: {r.status_code} {r.text}"

    if role == "admin":
        asyncio.run(_promote_to_admin(email))

    login = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass1"})
    assert login.status_code == 200
    return login.json()["access_token"]


# One app + TestClient for the entire module to avoid async engine event-loop conflicts.
@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(), raise_server_exceptions=True) as c:
        yield c


class TestZonesCrudAgainstRealDb:
    def test_create_zone(self, client):
        token = _register_and_get_token(client)
        suffix = str(time.time_ns())
        r = client.post(
            "/api/v1/zones",
            json=_zone_payload(suffix),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == f"DBZone {suffix}"
        assert body["country"] == f"DBCountry{suffix}"
        assert "id" in body
        assert body["latitude"] == 4.5
        assert body["longitude"] == -74.1

    def test_create_duplicate_zone_returns_409(self, client):
        token = _register_and_get_token(client)
        suffix = str(time.time_ns())
        payload = _zone_payload(suffix)
        r1 = client.post("/api/v1/zones", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert r1.status_code == 201
        r2 = client.post("/api/v1/zones", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 409
        assert r2.json()["error"] == "ZONE_NAME_EXISTS"

    def test_get_zone(self, client):
        token = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = client.post(
            "/api/v1/zones",
            json=_zone_payload(suffix),
            headers={"Authorization": f"Bearer {token}"},
        ).json()["id"]

        r = client.get(f"/api/v1/zones/{zone_id}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["id"] == zone_id

    def test_get_zone_not_found(self, client):
        token = _register_and_get_token(client)
        r = client.get(f"/api/v1/zones/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 404
        assert r.json()["error"] == "ZONE_NOT_FOUND"

    def test_list_zones_returns_created_zone(self, client):
        token = _register_and_get_token(client)
        suffix = str(time.time_ns())
        client.post(
            "/api/v1/zones",
            json=_zone_payload(suffix),
            headers={"Authorization": f"Bearer {token}"},
        )
        r = client.get("/api/v1/zones", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        names = [z["name"] for z in body["items"]]
        assert f"DBZone {suffix}" in names

    def test_list_zones_country_filter(self, client):
        token = _register_and_get_token(client)
        suffix = str(time.time_ns())
        unique_country = f"UniqueDBCountry{suffix}"
        client.post(
            "/api/v1/zones",
            json=_zone_payload(suffix, country=unique_country),
            headers={"Authorization": f"Bearer {token}"},
        )
        r = client.get(
            f"/api/v1/zones?country={unique_country}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["country"] == unique_country

    def test_list_zones_country_filter_case_insensitive(self, client):
        token = _register_and_get_token(client)
        suffix = str(time.time_ns())
        unique_country = f"CasedCountry{suffix}"
        client.post(
            "/api/v1/zones",
            json=_zone_payload(suffix, country=unique_country),
            headers={"Authorization": f"Bearer {token}"},
        )
        r = client.get(
            f"/api/v1/zones?country={unique_country.upper()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_list_zones_country_filter_returns_empty_for_nonexistent(self, client):
        token = _register_and_get_token(client)
        r = client.get(
            "/api/v1/zones?country=CountryThatNeverExists99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_update_zone(self, client):
        token = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = client.post(
            "/api/v1/zones",
            json=_zone_payload(suffix),
            headers={"Authorization": f"Bearer {token}"},
        ).json()["id"]

        new_name = f"Updated DBZone {suffix}"
        r = client.patch(
            f"/api/v1/zones/{zone_id}",
            json={"name": new_name},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["name"] == new_name

    def test_delete_zone(self, client):
        token = _register_and_get_token(client, role="admin")
        suffix = str(time.time_ns())
        zone_id = client.post(
            "/api/v1/zones",
            json=_zone_payload(suffix),
            headers={"Authorization": f"Bearer {token}"},
        ).json()["id"]

        r = client.delete(f"/api/v1/zones/{zone_id}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 204

        r2 = client.get(f"/api/v1/zones/{zone_id}", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 404

    def test_deleted_zone_excluded_from_list(self, client):
        token = _register_and_get_token(client, role="admin")
        suffix = str(time.time_ns())
        unique_country = f"DeletedDBCountry{suffix}"
        zone_id = client.post(
            "/api/v1/zones",
            json=_zone_payload(suffix, country=unique_country),
            headers={"Authorization": f"Bearer {token}"},
        ).json()["id"]

        client.delete(f"/api/v1/zones/{zone_id}", headers={"Authorization": f"Bearer {token}"})

        r = client.get(
            f"/api/v1/zones?country={unique_country}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_geom_column_populated_after_create(self, client):
        """Verify PostGIS geom column is set by querying the DB directly via asyncpg."""
        settings = get_settings()
        token = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = client.post(
            "/api/v1/zones",
            json=_zone_payload(suffix, latitude=4.711, longitude=-74.072),
            headers={"Authorization": f"Bearer {token}"},
        ).json()["id"]

        async def _check_geom() -> str:
            conn = await asyncpg.connect(
                host=settings.postgres_host,
                port=int(settings.postgres_port),
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
            )
            try:
                return await conn.fetchval(
                    "SELECT ST_AsText(geom) FROM zones WHERE id = $1",
                    uuid.UUID(zone_id),
                )
            finally:
                await conn.close()

        wkt = asyncio.run(_check_geom())
        assert wkt is not None
        assert "POINT" in wkt
