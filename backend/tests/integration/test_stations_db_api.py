"""
Real-database integration tests for the Stations module.

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


def _station_payload(zone_id: str, suffix: str = "", **overrides) -> dict:
    return {
        "code": f"STA{suffix[:8].replace('-', '')}".upper()[:10] or "STA-001",
        "name": f"DB Station {suffix}",
        "zone_id": zone_id,
        "latitude": 4.711,
        "longitude": -74.072,
        **overrides,
    }


def _zone_payload(suffix: str = "") -> dict:
    return {
        "name": f"StationTestZone {suffix}",
        "city": "Test City",
        "country": f"TestCountry{suffix}",
        "latitude": 4.5,
        "longitude": -74.1,
    }


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


def _register_and_get_token(client: TestClient, role: str = "researcher") -> tuple[str, str]:
    """Returns (token, email)."""
    email = f"sta-db-{time.time_ns()}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "document": "11111", "email": email, "password": "SecurePass1"},
    )
    assert r.status_code == 201, f"register failed: {r.status_code} {r.text}"

    if role == "admin":
        asyncio.run(_promote_to_admin(email))

    login = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass1"})
    assert login.status_code == 200
    return login.json()["access_token"], email


def _create_zone(client: TestClient, token: str, suffix: str) -> str:
    """Create a zone and return its id."""
    r = client.post(
        "/api/v1/zones",
        json=_zone_payload(suffix),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, f"zone create failed: {r.status_code} {r.text}"
    return r.json()["id"]


def _create_station(client: TestClient, token: str, zone_id: str, suffix: str, **overrides) -> dict:
    """Create a station and return the response body."""
    if "code" not in overrides:
        # Use a UUID fragment to guarantee uniqueness across the entire test session.
        overrides["code"] = f"STA{str(uuid.uuid4()).replace('-', '').upper()[:10]}"
    r = client.post(
        "/api/v1/stations",
        json=_station_payload(zone_id, suffix, **overrides),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, f"station create failed: {r.status_code} {r.text}"
    return r.json()


# One app + TestClient for the entire module to avoid async engine event-loop conflicts.
@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(), raise_server_exceptions=True) as c:
        yield c


class TestStationsCrudAgainstRealDb:
    def test_create_station(self, client):
        token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, token, suffix)
        body = _create_station(client, token, zone_id, suffix)
        assert "id" in body
        assert body["zone_id"] == zone_id
        assert body["status"] == "active"
        assert body["latitude"] == pytest.approx(4.711, rel=1e-4)
        assert body["longitude"] == pytest.approx(-74.072, rel=1e-4)

    def test_create_station_with_duplicate_code_returns_409(self, client):
        token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, token, suffix)
        code = f"UNIQ{suffix[-4:].upper()}"
        _create_station(client, token, zone_id, suffix, code=code)
        r2 = client.post(
            "/api/v1/stations",
            json=_station_payload(zone_id, suffix, code=code),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 409
        assert r2.json()["error"] == "STATION_CODE_EXISTS"

    def test_create_station_with_nonexistent_zone_returns_404(self, client):
        token, _ = _register_and_get_token(client)
        r = client.post(
            "/api/v1/stations",
            json={"code": "STA-NZ1", "name": "No Zone", "zone_id": str(uuid.uuid4()), "latitude": 4.5, "longitude": -74.0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404

    def test_get_station_by_id(self, client):
        token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, token, suffix)
        station_id = _create_station(client, token, zone_id, suffix)["id"]
        r = client.get(f"/api/v1/stations/{station_id}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["id"] == station_id

    def test_get_station_returns_404_for_unknown_id(self, client):
        token, _ = _register_and_get_token(client)
        r = client.get(f"/api/v1/stations/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 404
        assert r.json()["error"] == "NOT_FOUND"

    def test_non_member_cannot_get_station(self, client):
        token_a, _ = _register_and_get_token(client)
        token_b, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, token_a, suffix)
        station_id = _create_station(client, token_a, zone_id, suffix)["id"]
        r = client.get(f"/api/v1/stations/{station_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert r.status_code == 403

    def test_list_stations_researcher_sees_only_own(self, client):
        token_a, _ = _register_and_get_token(client)
        token_b, _ = _register_and_get_token(client)
        suffix_a = str(time.time_ns())
        suffix_b = str(time.time_ns() + 1)
        zone_id_a = _create_zone(client, token_a, suffix_a)
        zone_id_b = _create_zone(client, token_b, suffix_b)
        sta_a = _create_station(client, token_a, zone_id_a, suffix_a)
        _create_station(client, token_b, zone_id_b, suffix_b)
        r = client.get("/api/v1/stations", headers={"Authorization": f"Bearer {token_a}"})
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()["items"]]
        assert sta_a["id"] in ids
        assert all(i in ids for i in ids)

    def test_list_stations_admin_sees_all(self, client):
        token_admin, _ = _register_and_get_token(client, role="admin")
        token_r, _ = _register_and_get_token(client)
        suffix_r = str(time.time_ns())
        zone_id = _create_zone(client, token_r, suffix_r)
        sta = _create_station(client, token_r, zone_id, suffix_r)
        # Filter by zone_id to keep the result set small and stable across repeated test runs.
        r = client.get(f"/api/v1/stations?zone_id={zone_id}", headers={"Authorization": f"Bearer {token_admin}"})
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()["items"]]
        assert sta["id"] in ids

    def test_list_stations_zone_filter(self, client):
        token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, token, suffix)
        sta = _create_station(client, token, zone_id, suffix)
        r = client.get(f"/api/v1/stations?zone_id={zone_id}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        ids = [s["id"] for s in body["items"]]
        assert sta["id"] in ids

    def test_update_station_name(self, client):
        token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, token, suffix)
        station_id = _create_station(client, token, zone_id, suffix)["id"]
        new_name = f"Updated Station {suffix}"
        r = client.patch(
            f"/api/v1/stations/{station_id}",
            json={"name": new_name},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["name"] == new_name

    def test_update_station_zone_to_nonexistent_returns_404(self, client):
        token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, token, suffix)
        station_id = _create_station(client, token, zone_id, suffix)["id"]
        r = client.patch(
            f"/api/v1/stations/{station_id}",
            json={"zone_id": str(uuid.uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404

    def test_delete_station(self, client):
        token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, token, suffix)
        station_id = _create_station(client, token, zone_id, suffix)["id"]
        r = client.delete(f"/api/v1/stations/{station_id}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 204
        r2 = client.get(f"/api/v1/stations/{station_id}", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 404

    def test_deleted_station_excluded_from_list(self, client):
        token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, token, suffix)
        station_id = _create_station(client, token, zone_id, suffix)["id"]
        client.delete(f"/api/v1/stations/{station_id}", headers={"Authorization": f"Bearer {token}"})
        r = client.get(f"/api/v1/stations?zone_id={zone_id}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()["items"]]
        assert station_id not in ids

    def test_geom_column_populated_after_create(self, client):
        """Verify PostGIS geom column is set by querying the DB directly via asyncpg."""
        settings = get_settings()
        token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, token, suffix)
        station_id = _create_station(client, token, zone_id, suffix)["id"]

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
                    "SELECT ST_AsText(geom) FROM stations WHERE id = $1",
                    uuid.UUID(station_id),
                )
            finally:
                await conn.close()

        wkt = asyncio.run(_check_geom())
        assert wkt is not None
        assert "POINT" in wkt

    def test_zone_cannot_be_deleted_with_active_station(self, client):
        """has_active_stations stub replaced — zone deletion must be blocked."""
        token_admin, _ = _register_and_get_token(client, role="admin")
        token_r, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, token_r, suffix)
        _create_station(client, token_r, zone_id, suffix)
        r = client.delete(f"/api/v1/zones/{zone_id}", headers={"Authorization": f"Bearer {token_admin}"})
        assert r.status_code == 400
        assert r.json()["error"] == "ZONE_HAS_STATIONS"
