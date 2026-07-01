"""
Real-database integration tests for the Station Foods module.

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
    email = f"sf-db-{time.time_ns()}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "document": "77777", "email": email, "password": "SecurePass1"},
    )
    assert r.status_code == 201
    if role == "admin":
        asyncio.run(_promote_to_admin(email))
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass1"})
    assert login.status_code == 200
    return login.json()["access_token"], email


def _create_zone(client: TestClient, token: str) -> str:
    r = client.post(
        "/api/v1/zones",
        json={"name": f"Zone {uuid.uuid4().hex[:6]}", "city": "Test", "country": "CO",
              "latitude": 4.0, "longitude": -74.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    return r.json()["id"]


def _create_station(client: TestClient, token: str, zone_id: str) -> str:
    r = client.post(
        "/api/v1/stations",
        json={"code": f"SF{uuid.uuid4().hex[:8].upper()}", "name": "Station",
              "zone_id": zone_id, "latitude": 4.0, "longitude": -74.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    return r.json()["id"]


def _create_food(client: TestClient, token: str) -> str:
    r = client.post(
        "/api/v1/foods",
        json={"name": f"Food-{uuid.uuid4().hex[:8]}", "type": "seeds"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(), raise_server_exceptions=True) as c:
        yield c


class TestStationFoodsCrudAgainstRealDb:
    def test_add_food_to_station(self, client):
        res_token, _ = _register_and_get_token(client)
        zone_id = _create_zone(client, res_token)
        station_id = _create_station(client, res_token, zone_id)
        food_id = _create_food(client, res_token)

        r = client.post(
            f"/api/v1/stations/{station_id}/foods",
            json={"food_id": food_id, "active": True},
            headers={"Authorization": f"Bearer {res_token}"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["active"] is True
        assert body["food_id"] == food_id
        assert body["food_name"] is not None

    def test_add_food_deactivates_previous_active(self, client):
        res_token, _ = _register_and_get_token(client)
        zone_id = _create_zone(client, res_token)
        station_id = _create_station(client, res_token, zone_id)
        food_a = _create_food(client, res_token)
        food_b = _create_food(client, res_token)

        sf_a = client.post(
            f"/api/v1/stations/{station_id}/foods",
            json={"food_id": food_a, "active": True},
            headers={"Authorization": f"Bearer {res_token}"},
        ).json()

        client.post(
            f"/api/v1/stations/{station_id}/foods",
            json={"food_id": food_b, "active": True},
            headers={"Authorization": f"Bearer {res_token}"},
        )

        list_r = client.get(
            f"/api/v1/stations/{station_id}/foods",
            headers={"Authorization": f"Bearer {res_token}"},
        )
        items = {i["id"]: i["active"] for i in list_r.json()["items"]}
        assert items[sf_a["id"]] is False

    def test_food_already_associated_returns_409(self, client):
        res_token, _ = _register_and_get_token(client)
        zone_id = _create_zone(client, res_token)
        station_id = _create_station(client, res_token, zone_id)
        food_id = _create_food(client, res_token)

        client.post(
            f"/api/v1/stations/{station_id}/foods",
            json={"food_id": food_id},
            headers={"Authorization": f"Bearer {res_token}"},
        )
        r2 = client.post(
            f"/api/v1/stations/{station_id}/foods",
            json={"food_id": food_id},
            headers={"Authorization": f"Bearer {res_token}"},
        )
        assert r2.status_code == 409
        assert r2.json()["error"] == "FOOD_ALREADY_ASSOCIATED"

    def test_activate_swaps_active_food_no_integrity_error(self, client):
        """Food A active, Food B inactive → PATCH activate Food B → 200, A inactive, B active."""
        res_token, _ = _register_and_get_token(client)
        zone_id = _create_zone(client, res_token)
        station_id = _create_station(client, res_token, zone_id)
        food_a = _create_food(client, res_token)
        food_b = _create_food(client, res_token)

        sf_a = client.post(
            f"/api/v1/stations/{station_id}/foods",
            json={"food_id": food_a, "active": True},
            headers={"Authorization": f"Bearer {res_token}"},
        ).json()

        sf_b = client.post(
            f"/api/v1/stations/{station_id}/foods",
            json={"food_id": food_b, "active": False},
            headers={"Authorization": f"Bearer {res_token}"},
        ).json()

        r = client.patch(
            f"/api/v1/stations/{station_id}/foods/{sf_b['id']}/activate",
            headers={"Authorization": f"Bearer {res_token}"},
        )
        assert r.status_code == 200
        assert r.json()["active"] is True

        list_r = client.get(
            f"/api/v1/stations/{station_id}/foods",
            headers={"Authorization": f"Bearer {res_token}"},
        )
        items = {i["id"]: i["active"] for i in list_r.json()["items"]}
        assert items[sf_a["id"]] is False
        assert items[sf_b["id"]] is True

    def test_activate_deactivate_cycle(self, client):
        res_token, _ = _register_and_get_token(client)
        zone_id = _create_zone(client, res_token)
        station_id = _create_station(client, res_token, zone_id)
        food_id = _create_food(client, res_token)

        sf = client.post(
            f"/api/v1/stations/{station_id}/foods",
            json={"food_id": food_id, "active": True},
            headers={"Authorization": f"Bearer {res_token}"},
        ).json()

        r_deact = client.patch(
            f"/api/v1/stations/{station_id}/foods/{sf['id']}/deactivate",
            headers={"Authorization": f"Bearer {res_token}"},
        )
        assert r_deact.status_code == 200
        assert r_deact.json()["active"] is False

        r_act = client.patch(
            f"/api/v1/stations/{station_id}/foods/{sf['id']}/activate",
            headers={"Authorization": f"Bearer {res_token}"},
        )
        assert r_act.status_code == 200
        assert r_act.json()["active"] is True

    def test_cannot_remove_active_food_returns_400(self, client):
        res_token, _ = _register_and_get_token(client)
        zone_id = _create_zone(client, res_token)
        station_id = _create_station(client, res_token, zone_id)
        food_id = _create_food(client, res_token)

        sf = client.post(
            f"/api/v1/stations/{station_id}/foods",
            json={"food_id": food_id, "active": True},
            headers={"Authorization": f"Bearer {res_token}"},
        ).json()

        r = client.delete(
            f"/api/v1/stations/{station_id}/foods/{sf['id']}",
            headers={"Authorization": f"Bearer {res_token}"},
        )
        assert r.status_code == 400
        assert r.json()["error"] == "CANNOT_REMOVE_ACTIVE"

    def test_remove_inactive_food_returns_204(self, client):
        res_token, _ = _register_and_get_token(client)
        zone_id = _create_zone(client, res_token)
        station_id = _create_station(client, res_token, zone_id)
        food_id = _create_food(client, res_token)

        sf = client.post(
            f"/api/v1/stations/{station_id}/foods",
            json={"food_id": food_id, "active": False},
            headers={"Authorization": f"Bearer {res_token}"},
        ).json()

        r = client.delete(
            f"/api/v1/stations/{station_id}/foods/{sf['id']}",
            headers={"Authorization": f"Bearer {res_token}"},
        )
        assert r.status_code == 204

    def test_delete_food_catalog_blocked_when_active_at_station(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        res_token, _ = _register_and_get_token(client)
        zone_id = _create_zone(client, res_token)
        station_id = _create_station(client, res_token, zone_id)
        food_id = _create_food(client, admin_token)

        client.post(
            f"/api/v1/stations/{station_id}/foods",
            json={"food_id": food_id, "active": True},
            headers={"Authorization": f"Bearer {res_token}"},
        )

        r = client.delete(
            f"/api/v1/foods/{food_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 400
        assert r.json()["error"] == "FOOD_IN_USE"
