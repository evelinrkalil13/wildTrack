"""
Real-database integration tests for the Devices module.

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


def _zone_payload(suffix: str = "") -> dict:
    return {
        "name": f"DevTestZone {suffix}",
        "city": "Test City",
        "country": f"DevCountry{suffix}",
        "latitude": 4.5,
        "longitude": -74.1,
    }


def _station_payload(zone_id: str, suffix: str = "") -> dict:
    return {
        "code": f"STA{str(uuid.uuid4()).replace('-', '').upper()[:10]}",
        "name": f"Dev Station {suffix}",
        "zone_id": zone_id,
        "latitude": 4.711,
        "longitude": -74.072,
    }


def _device_payload(**overrides) -> dict:
    serial = f"WT-{str(uuid.uuid4()).replace('-', '').upper()[:10]}"
    return {"serial_number": serial, "name": "Feeder Alpha", **overrides}


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
    """Returns (token, email)."""
    email = f"dev-db-{time.time_ns()}@example.com"
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
    r = client.post(
        "/api/v1/zones",
        json=_zone_payload(suffix),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, f"zone create failed: {r.status_code} {r.text}"
    return r.json()["id"]


def _create_station(client: TestClient, token: str, zone_id: str, suffix: str) -> str:
    r = client.post(
        "/api/v1/stations",
        json=_station_payload(zone_id, suffix),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, f"station create failed: {r.status_code} {r.text}"
    return r.json()["id"]


def _create_device(client: TestClient, token: str, **overrides) -> dict:
    r = client.post(
        "/api/v1/devices",
        json=_device_payload(**overrides),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, f"device create failed: {r.status_code} {r.text}"
    return r.json()


# One app + TestClient for the entire module to avoid async engine event-loop conflicts.
@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(), raise_server_exceptions=True) as c:
        yield c


class TestDevicesCrudAgainstRealDb:
    def test_create_device_returns_201_unassigned(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        device = _create_device(client, admin_token)
        assert "id" in device
        assert device["status"] == "unassigned"
        assert device["station_id"] is None
        assert device["station_code"] is None

    def test_create_device_with_mac_address(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        device = _create_device(client, admin_token, mac_address="AA:BB:CC:DD:EE:FF")
        assert device["mac_address"] == "AA:BB:CC:DD:EE:FF"

    def test_create_device_with_duplicate_serial_returns_409(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        serial = f"WT-SERIAL-{time.time_ns()}"
        _create_device(client, admin_token, serial_number=serial)
        r2 = client.post(
            "/api/v1/devices",
            json={"serial_number": serial},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r2.status_code == 409
        assert r2.json()["error"] == "SERIAL_EXISTS"

    def test_non_admin_cannot_create_device(self, client):
        res_token, _ = _register_and_get_token(client)
        r = client.post(
            "/api/v1/devices",
            json=_device_payload(),
            headers={"Authorization": f"Bearer {res_token}"},
        )
        assert r.status_code == 403

    def test_admin_can_get_any_device(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        device = _create_device(client, admin_token)
        r = client.get(
            f"/api/v1/devices/{device['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200
        assert r.json()["id"] == device["id"]

    def test_non_admin_cannot_get_unassigned_device(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        res_token, _ = _register_and_get_token(client)
        device = _create_device(client, admin_token)
        r = client.get(
            f"/api/v1/devices/{device['id']}",
            headers={"Authorization": f"Bearer {res_token}"},
        )
        assert r.status_code == 403

    def test_get_device_returns_404_for_unknown_id(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        r = client.get(
            f"/api/v1/devices/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 404
        assert r.json()["error"] == "NOT_FOUND"

    def test_assign_device_to_station(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        res_token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, res_token, suffix)
        station_id = _create_station(client, res_token, zone_id, suffix)
        device = _create_device(client, admin_token)

        r = client.patch(
            f"/api/v1/devices/{device['id']}/assign",
            json={"station_id": station_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "online"
        assert body["station_id"] == station_id

    def test_researcher_can_get_device_on_their_station(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        res_token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, res_token, suffix)
        station_id = _create_station(client, res_token, zone_id, suffix)
        device = _create_device(client, admin_token)
        client.patch(
            f"/api/v1/devices/{device['id']}/assign",
            json={"station_id": station_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        r = client.get(
            f"/api/v1/devices/{device['id']}",
            headers={"Authorization": f"Bearer {res_token}"},
        )
        assert r.status_code == 200
        assert r.json()["station_code"] is not None

    def test_assign_already_assigned_device_returns_400(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        res_token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, res_token, suffix)
        station_id = _create_station(client, res_token, zone_id, suffix)
        device = _create_device(client, admin_token)
        client.patch(
            f"/api/v1/devices/{device['id']}/assign",
            json={"station_id": station_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        r = client.patch(
            f"/api/v1/devices/{device['id']}/assign",
            json={"station_id": station_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 400
        assert r.json()["error"] == "DEVICE_ALREADY_ASSIGNED"

    def test_station_cannot_have_two_active_devices(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        res_token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, res_token, suffix)
        station_id = _create_station(client, res_token, zone_id, suffix)
        device1 = _create_device(client, admin_token)
        device2 = _create_device(client, admin_token)

        client.patch(
            f"/api/v1/devices/{device1['id']}/assign",
            json={"station_id": station_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        r = client.patch(
            f"/api/v1/devices/{device2['id']}/assign",
            json={"station_id": station_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 400
        assert r.json()["error"] == "STATION_HAS_DEVICE"

    def test_unassign_device(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        res_token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, res_token, suffix)
        station_id = _create_station(client, res_token, zone_id, suffix)
        device = _create_device(client, admin_token)
        client.patch(
            f"/api/v1/devices/{device['id']}/assign",
            json={"station_id": station_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        r = client.patch(
            f"/api/v1/devices/{device['id']}/unassign",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "unassigned"
        assert body["station_id"] is None

    def test_unassign_unassigned_device_returns_400(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        device = _create_device(client, admin_token)
        r = client.patch(
            f"/api/v1/devices/{device['id']}/unassign",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 400
        assert r.json()["error"] == "DEVICE_NOT_ASSIGNED"

    def test_delete_device_returns_204(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        device = _create_device(client, admin_token)
        r = client.delete(
            f"/api/v1/devices/{device['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 204

        r2 = client.get(
            f"/api/v1/devices/{device['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r2.status_code == 404

    def test_admin_list_sees_unassigned_devices(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        device = _create_device(client, admin_token)
        r = client.get(
            f"/api/v1/devices?status=unassigned",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200
        ids = [d["id"] for d in r.json()["items"]]
        assert device["id"] in ids

    def test_researcher_list_excludes_unassigned_devices(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        res_token, _ = _register_and_get_token(client)
        device = _create_device(client, admin_token)
        # Researcher gets list — should NOT see the unassigned device
        r = client.get("/api/v1/devices", headers={"Authorization": f"Bearer {res_token}"})
        assert r.status_code == 200
        ids = [d["id"] for d in r.json()["items"]]
        assert device["id"] not in ids

    def test_delete_station_unassigns_device(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        res_token, _ = _register_and_get_token(client)
        suffix = str(time.time_ns())
        zone_id = _create_zone(client, res_token, suffix)
        station_id = _create_station(client, res_token, zone_id, suffix)
        device = _create_device(client, admin_token)

        # Assign device to station
        client.patch(
            f"/api/v1/devices/{device['id']}/assign",
            json={"station_id": station_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Delete the station (researcher is owner)
        r_del = client.delete(
            f"/api/v1/stations/{station_id}",
            headers={"Authorization": f"Bearer {res_token}"},
        )
        assert r_del.status_code == 204

        # Device should now be unassigned
        r_dev = client.get(
            f"/api/v1/devices/{device['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r_dev.status_code == 200
        body = r_dev.json()
        assert body["status"] == "unassigned"
        assert body["station_id"] is None
