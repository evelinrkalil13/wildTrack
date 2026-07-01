import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, require_admin
from app.main import create_app
from modules.animals.exceptions import AnimalNotFoundError, RfidTagConflictError
from modules.animals.schemas import AnimalListResponse, AnimalRead, AnimalStationsRead
from shared.enums import AnimalSex, UserRole
from unittest.mock import MagicMock


def _make_user(role: UserRole) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


def _make_animal_read(**kwargs) -> AnimalRead:
    now = datetime.now(timezone.utc)
    return AnimalRead(
        id=kwargs.get("id", uuid.uuid4()),
        rfid_tag=kwargs.get("rfid_tag", None),
        species=kwargs.get("species", "Tremarctos ornatus"),
        sex=kwargs.get("sex", AnimalSex.unknown),
        estimated_age=kwargs.get("estimated_age", None),
        is_identified=kwargs.get("is_identified", False),
        notes=kwargs.get("notes", None),
        created_at=kwargs.get("created_at", now),
        updated_at=kwargs.get("updated_at", now),
    )


def _make_auth_client(role: UserRole = UserRole.researcher) -> TestClient:
    app = create_app()
    fake_user = _make_user(role)
    app.dependency_overrides[get_current_user] = lambda: fake_user
    if role == UserRole.admin:
        app.dependency_overrides[require_admin] = lambda: fake_user
    return TestClient(app, raise_server_exceptions=False)


def _make_no_auth_client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /animals
# ---------------------------------------------------------------------------

class TestCreateAnimal:
    def test_creates_animal_returns_201(self):
        animal = _make_animal_read()
        client = _make_auth_client()
        with patch("modules.animals.router.AnimalService.create_animal", new=AsyncMock(return_value=animal)):
            r = client.post("/api/v1/animals", json={"species": "Tremarctos ornatus"})
        assert r.status_code == 201
        assert "id" in r.json()

    def test_creates_animal_with_rfid(self):
        animal = _make_animal_read(rfid_tag="RFID-001", is_identified=True)
        client = _make_auth_client()
        with patch("modules.animals.router.AnimalService.create_animal", new=AsyncMock(return_value=animal)):
            r = client.post("/api/v1/animals", json={"species": "Puma concolor", "rfid_tag": "RFID-001"})
        assert r.status_code == 201
        assert r.json()["is_identified"] is True

    def test_duplicate_rfid_returns_409(self):
        client = _make_auth_client()
        with patch("modules.animals.router.AnimalService.create_animal", new=AsyncMock(side_effect=RfidTagConflictError())):
            r = client.post("/api/v1/animals", json={"species": "Puma concolor", "rfid_tag": "RFID-001"})
        assert r.status_code == 409
        assert r.json()["error"] == "RFID_TAG_EXISTS"

    def test_missing_species_returns_422(self):
        client = _make_auth_client()
        r = client.post("/api/v1/animals", json={})
        assert r.status_code == 422

    def test_unauthenticated_returns_401(self):
        client = _make_no_auth_client()
        r = client.post("/api/v1/animals", json={"species": "Puma concolor"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /animals
# ---------------------------------------------------------------------------

class TestListAnimals:
    def test_returns_200_with_paginated_response(self):
        animals = [_make_animal_read() for _ in range(2)]
        response = AnimalListResponse(total=2, page=1, page_size=20, pages=1, items=animals)
        client = _make_auth_client()
        with patch("modules.animals.router.AnimalService.list_animals", new=AsyncMock(return_value=response)):
            r = client.get("/api/v1/animals")
        assert r.status_code == 200
        assert r.json()["total"] == 2

    def test_unauthenticated_returns_401(self):
        client = _make_no_auth_client()
        r = client.get("/api/v1/animals")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /animals/{id}
# ---------------------------------------------------------------------------

class TestGetAnimal:
    def test_returns_animal_read(self):
        animal = _make_animal_read()
        client = _make_auth_client()
        with patch("modules.animals.router.AnimalService.get_animal", new=AsyncMock(return_value=animal)):
            r = client.get(f"/api/v1/animals/{animal.id}")
        assert r.status_code == 200
        assert r.json()["id"] == str(animal.id)

    def test_unknown_id_returns_404(self):
        client = _make_auth_client()
        with patch("modules.animals.router.AnimalService.get_animal", new=AsyncMock(side_effect=AnimalNotFoundError())):
            r = client.get(f"/api/v1/animals/{uuid.uuid4()}")
        assert r.status_code == 404
        assert r.json()["error"] == "NOT_FOUND"

    def test_unauthenticated_returns_401(self):
        client = _make_no_auth_client()
        r = client.get(f"/api/v1/animals/{uuid.uuid4()}")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /animals/{id}
# ---------------------------------------------------------------------------

class TestUpdateAnimal:
    def test_updates_animal(self):
        animal = _make_animal_read(species="Updated species")
        client = _make_auth_client()
        with patch("modules.animals.router.AnimalService.update_animal", new=AsyncMock(return_value=animal)):
            r = client.patch(f"/api/v1/animals/{animal.id}", json={"species": "Updated species"})
        assert r.status_code == 200
        assert r.json()["species"] == "Updated species"

    def test_unknown_id_returns_404(self):
        client = _make_auth_client()
        with patch("modules.animals.router.AnimalService.update_animal", new=AsyncMock(side_effect=AnimalNotFoundError())):
            r = client.patch(f"/api/v1/animals/{uuid.uuid4()}", json={"species": "Updated species"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /animals/{id}
# ---------------------------------------------------------------------------

class TestDeleteAnimal:
    def test_admin_deletes_returns_204(self):
        client = _make_auth_client(UserRole.admin)
        with patch("modules.animals.router.AnimalService.delete_animal", new=AsyncMock()):
            r = client.delete(f"/api/v1/animals/{uuid.uuid4()}")
        assert r.status_code == 204

    def test_non_admin_returns_403(self):
        client = _make_auth_client(UserRole.researcher)
        r = client.delete(f"/api/v1/animals/{uuid.uuid4()}")
        assert r.status_code == 403

    def test_unknown_id_returns_404(self):
        client = _make_auth_client(UserRole.admin)
        with patch("modules.animals.router.AnimalService.delete_animal", new=AsyncMock(side_effect=AnimalNotFoundError())):
            r = client.delete(f"/api/v1/animals/{uuid.uuid4()}")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /animals/{id}/stations
# ---------------------------------------------------------------------------

class TestGetAnimalStations:
    def test_returns_200_with_empty_stations(self):
        animal_id = uuid.uuid4()
        stub = AnimalStationsRead(animal_id=animal_id, rfid_tag="RFID-001", stations=[])
        client = _make_auth_client()
        with patch("modules.animals.router.AnimalService.get_animal_stations", new=AsyncMock(return_value=stub)):
            r = client.get(f"/api/v1/animals/{animal_id}/stations")
        assert r.status_code == 200
        assert r.json()["stations"] == []
        assert r.json()["rfid_tag"] == "RFID-001"

    def test_unknown_animal_returns_404(self):
        client = _make_auth_client()
        with patch("modules.animals.router.AnimalService.get_animal_stations", new=AsyncMock(side_effect=AnimalNotFoundError())):
            r = client.get(f"/api/v1/animals/{uuid.uuid4()}/stations")
        assert r.status_code == 404
