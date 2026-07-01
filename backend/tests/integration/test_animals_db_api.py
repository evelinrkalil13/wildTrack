"""
Real-database integration tests for the Animals module.

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
    email = f"animals-db-{time.time_ns()}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "document": "99999", "email": email, "password": "SecurePass1"},
    )
    assert r.status_code == 201, f"register failed: {r.status_code} {r.text}"
    if role == "admin":
        asyncio.run(_promote_to_admin(email))
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass1"})
    assert login.status_code == 200
    return login.json()["access_token"], email


def _create_animal(client: TestClient, token: str, **overrides) -> dict:
    payload = {"species": f"Species {uuid.uuid4().hex[:6]}", **overrides}
    r = client.post(
        "/api/v1/animals",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, f"animal create failed: {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(), raise_server_exceptions=True) as c:
        yield c


class TestAnimalsCrudAgainstRealDb:
    def test_create_animal_without_rfid_is_identified_false(self, client):
        token, _ = _register_and_get_token(client)
        animal = _create_animal(client, token)
        assert animal["is_identified"] is False
        assert animal["rfid_tag"] is None

    def test_create_animal_with_rfid_is_identified_true(self, client):
        token, _ = _register_and_get_token(client)
        rfid = f"RFID-{uuid.uuid4().hex[:8].upper()}"
        animal = _create_animal(client, token, rfid_tag=rfid)
        assert animal["is_identified"] is True
        assert animal["rfid_tag"] == rfid

    def test_duplicate_rfid_returns_409(self, client):
        token, _ = _register_and_get_token(client)
        rfid = f"RFID-{uuid.uuid4().hex[:8].upper()}"
        _create_animal(client, token, rfid_tag=rfid)
        r = client.post(
            "/api/v1/animals",
            json={"species": "Other species", "rfid_tag": rfid},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 409
        assert r.json()["error"] == "RFID_TAG_EXISTS"

    def test_get_animal_returns_200(self, client):
        token, _ = _register_and_get_token(client)
        animal = _create_animal(client, token)
        r = client.get(
            f"/api/v1/animals/{animal['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["id"] == animal["id"]

    def test_get_unknown_animal_returns_404(self, client):
        token, _ = _register_and_get_token(client)
        r = client.get(
            f"/api/v1/animals/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404
        assert r.json()["error"] == "NOT_FOUND"

    def test_update_adds_rfid_sets_is_identified_true(self, client):
        token, _ = _register_and_get_token(client)
        animal = _create_animal(client, token)
        assert animal["is_identified"] is False
        rfid = f"RFID-{uuid.uuid4().hex[:8].upper()}"
        r = client.patch(
            f"/api/v1/animals/{animal['id']}",
            json={"rfid_tag": rfid},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["is_identified"] is True
        assert r.json()["rfid_tag"] == rfid

    def test_list_with_species_filter(self, client):
        token, _ = _register_and_get_token(client)
        unique_species = f"UniqueSpecies{uuid.uuid4().hex[:6]}"
        _create_animal(client, token, species=unique_species)
        r = client.get(
            f"/api/v1/animals?species={unique_species}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_list_with_is_identified_filter(self, client):
        token, _ = _register_and_get_token(client)
        rfid = f"RFID-{uuid.uuid4().hex[:8].upper()}"
        _create_animal(client, token, rfid_tag=rfid)
        r = client.get(
            "/api/v1/animals?is_identified=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["is_identified"] is True

    def test_get_animal_stations_returns_empty_list(self, client):
        token, _ = _register_and_get_token(client)
        animal = _create_animal(client, token)
        r = client.get(
            f"/api/v1/animals/{animal['id']}/stations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["stations"] == []

    def test_admin_deletes_animal(self, client):
        admin_token, _ = _register_and_get_token(client, role="admin")
        animal = _create_animal(client, admin_token)
        r = client.delete(
            f"/api/v1/animals/{animal['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 204
        r2 = client.get(
            f"/api/v1/animals/{animal['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r2.status_code == 404

    def test_non_admin_cannot_delete(self, client):
        token, _ = _register_and_get_token(client)
        animal = _create_animal(client, token)
        r = client.delete(
            f"/api/v1/animals/{animal['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403
