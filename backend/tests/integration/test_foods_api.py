import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, require_admin, require_researcher_or_above
from app.main import create_app
from modules.foods.exceptions import FoodInUseError, FoodNameConflictError, FoodNotFoundError
from modules.foods.schemas import FoodListResponse, FoodRead
from shared.enums import UserRole


def _make_user(role: UserRole) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


def _make_food_read(**kwargs) -> FoodRead:
    now = datetime.now(timezone.utc)
    return FoodRead(
        id=kwargs.get("id", uuid.uuid4()),
        name=kwargs.get("name", "Mixed Seeds"),
        type=kwargs.get("type", "seeds"),
        description=kwargs.get("description", None),
        created_at=kwargs.get("created_at", now),
        updated_at=kwargs.get("updated_at", now),
    )


def _make_auth_client(role: UserRole = UserRole.researcher) -> TestClient:
    app = create_app()
    fake_user = _make_user(role)
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[require_researcher_or_above] = lambda: fake_user
    if role == UserRole.admin:
        app.dependency_overrides[require_admin] = lambda: fake_user
    return TestClient(app, raise_server_exceptions=False)


def _make_field_operator_client() -> TestClient:
    app = create_app()
    fake_user = _make_user(UserRole.field_operator)
    app.dependency_overrides[get_current_user] = lambda: fake_user
    return TestClient(app, raise_server_exceptions=False)


def _make_no_auth_client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /foods
# ---------------------------------------------------------------------------

class TestCreateFood:
    def test_researcher_creates_food_returns_201(self):
        food = _make_food_read()
        client = _make_auth_client(UserRole.researcher)
        with patch("modules.foods.router.FoodService.create_food", new=AsyncMock(return_value=food)):
            r = client.post("/api/v1/foods", json={"name": "Mixed Seeds", "type": "seeds"})
        assert r.status_code == 201
        assert "id" in r.json()

    def test_admin_creates_food_returns_201(self):
        food = _make_food_read()
        client = _make_auth_client(UserRole.admin)
        with patch("modules.foods.router.FoodService.create_food", new=AsyncMock(return_value=food)):
            r = client.post("/api/v1/foods", json={"name": "Mixed Seeds", "type": "seeds"})
        assert r.status_code == 201

    def test_field_operator_cannot_create_returns_403(self):
        client = _make_field_operator_client()
        r = client.post("/api/v1/foods", json={"name": "Mixed Seeds", "type": "seeds"})
        assert r.status_code == 403

    def test_duplicate_name_returns_409(self):
        client = _make_auth_client()
        with patch("modules.foods.router.FoodService.create_food", new=AsyncMock(side_effect=FoodNameConflictError())):
            r = client.post("/api/v1/foods", json={"name": "Mixed Seeds", "type": "seeds"})
        assert r.status_code == 409
        assert r.json()["error"] == "FOOD_NAME_EXISTS"

    def test_missing_required_fields_returns_422(self):
        client = _make_auth_client()
        r = client.post("/api/v1/foods", json={"name": "Seeds"})
        assert r.status_code == 422

    def test_unauthenticated_returns_401(self):
        client = _make_no_auth_client()
        r = client.post("/api/v1/foods", json={"name": "Seeds", "type": "seeds"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /foods
# ---------------------------------------------------------------------------

class TestListFoods:
    def test_returns_200_paginated(self):
        foods = [_make_food_read() for _ in range(3)]
        response = FoodListResponse(total=3, page=1, page_size=20, pages=1, items=foods)
        client = _make_auth_client()
        with patch("modules.foods.router.FoodService.list_foods", new=AsyncMock(return_value=response)):
            r = client.get("/api/v1/foods")
        assert r.status_code == 200
        assert r.json()["total"] == 3

    def test_unauthenticated_returns_401(self):
        client = _make_no_auth_client()
        r = client.get("/api/v1/foods")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /foods/{id}
# ---------------------------------------------------------------------------

class TestGetFood:
    def test_returns_food(self):
        food = _make_food_read()
        client = _make_auth_client()
        with patch("modules.foods.router.FoodService.get_food", new=AsyncMock(return_value=food)):
            r = client.get(f"/api/v1/foods/{food.id}")
        assert r.status_code == 200
        assert r.json()["name"] == food.name

    def test_unknown_id_returns_404(self):
        client = _make_auth_client()
        with patch("modules.foods.router.FoodService.get_food", new=AsyncMock(side_effect=FoodNotFoundError())):
            r = client.get(f"/api/v1/foods/{uuid.uuid4()}")
        assert r.status_code == 404
        assert r.json()["error"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# PATCH /foods/{id}
# ---------------------------------------------------------------------------

class TestUpdateFood:
    def test_updates_food(self):
        food = _make_food_read(name="New Name")
        client = _make_auth_client()
        with patch("modules.foods.router.FoodService.update_food", new=AsyncMock(return_value=food)):
            r = client.patch(f"/api/v1/foods/{food.id}", json={"name": "New Name"})
        assert r.status_code == 200
        assert r.json()["name"] == "New Name"

    def test_duplicate_name_returns_409(self):
        client = _make_auth_client()
        with patch("modules.foods.router.FoodService.update_food", new=AsyncMock(side_effect=FoodNameConflictError())):
            r = client.patch(f"/api/v1/foods/{uuid.uuid4()}", json={"name": "Taken"})
        assert r.status_code == 409

    def test_field_operator_cannot_update_returns_403(self):
        client = _make_field_operator_client()
        r = client.patch(f"/api/v1/foods/{uuid.uuid4()}", json={"name": "New"})
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /foods/{id}
# ---------------------------------------------------------------------------

class TestDeleteFood:
    def test_admin_deletes_food_returns_204(self):
        client = _make_auth_client(UserRole.admin)
        with patch("modules.foods.router.FoodService.delete_food", new=AsyncMock()):
            r = client.delete(f"/api/v1/foods/{uuid.uuid4()}")
        assert r.status_code == 204

    def test_researcher_cannot_delete_returns_403(self):
        client = _make_auth_client(UserRole.researcher)
        r = client.delete(f"/api/v1/foods/{uuid.uuid4()}")
        assert r.status_code == 403

    def test_food_in_use_returns_400(self):
        client = _make_auth_client(UserRole.admin)
        with patch("modules.foods.router.FoodService.delete_food", new=AsyncMock(side_effect=FoodInUseError())):
            r = client.delete(f"/api/v1/foods/{uuid.uuid4()}")
        assert r.status_code == 400
        assert r.json()["error"] == "FOOD_IN_USE"

    def test_unknown_id_returns_404(self):
        client = _make_auth_client(UserRole.admin)
        with patch("modules.foods.router.FoodService.delete_food", new=AsyncMock(side_effect=FoodNotFoundError())):
            r = client.delete(f"/api/v1/foods/{uuid.uuid4()}")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /foods/{id}/stations
# ---------------------------------------------------------------------------

class TestGetFoodStations:
    def _make_station_list_response(self, n: int = 1):
        from modules.station_foods.schemas import FoodStationListResponse, FoodStationRead
        now = datetime.now(timezone.utc)
        items = [
            FoodStationRead(
                station_id=uuid.uuid4(),
                station_code=f"EST-00{i + 1}",
                station_name=f"Feeder {i + 1}",
                active=True,
                created_at=now,
            )
            for i in range(n)
        ]
        return FoodStationListResponse(total=n, items=items)

    def test_returns_200_with_station_list(self):
        response = self._make_station_list_response(2)
        client = _make_auth_client()
        with patch("modules.foods.router.StationFoodService.get_food_stations", new=AsyncMock(return_value=response)):
            r = client.get(f"/api/v1/foods/{uuid.uuid4()}/stations")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert data["items"][0]["station_code"] == "EST-001"

    def test_returns_empty_list_when_no_stations(self):
        from modules.station_foods.schemas import FoodStationListResponse
        response = FoodStationListResponse(total=0, items=[])
        client = _make_auth_client()
        with patch("modules.foods.router.StationFoodService.get_food_stations", new=AsyncMock(return_value=response)):
            r = client.get(f"/api/v1/foods/{uuid.uuid4()}/stations")
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["items"] == []

    def test_unknown_food_returns_404(self):
        client = _make_auth_client()
        with patch("modules.foods.router.StationFoodService.get_food_stations", new=AsyncMock(side_effect=FoodNotFoundError())):
            r = client.get(f"/api/v1/foods/{uuid.uuid4()}/stations")
        assert r.status_code == 404
        assert r.json()["error"] == "NOT_FOUND"

    def test_unauthenticated_returns_401(self):
        client = _make_no_auth_client()
        r = client.get(f"/api/v1/foods/{uuid.uuid4()}/stations")
        assert r.status_code == 401
