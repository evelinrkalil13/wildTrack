import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import create_app
from modules.foods.exceptions import FoodNotFoundError
from modules.station_foods.exceptions import (
    CannotRemoveActiveFoodError,
    FoodAlreadyAssociatedError,
    StationFoodAccessDeniedError,
    StationFoodNotFoundError,
)
from modules.station_foods.schemas import StationFoodListResponse, StationFoodRead
from modules.stations.exceptions import StationNotFoundError
from shared.enums import UserRole


def _make_user(role: UserRole) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


def _make_sf_read(**kwargs) -> StationFoodRead:
    now = datetime.now(timezone.utc)
    return StationFoodRead(
        id=kwargs.get("id", uuid.uuid4()),
        station_id=kwargs.get("station_id", uuid.uuid4()),
        food_id=kwargs.get("food_id", uuid.uuid4()),
        food_name=kwargs.get("food_name", "Mixed Seeds"),
        food_type=kwargs.get("food_type", "seeds"),
        active=kwargs.get("active", True),
        created_at=kwargs.get("created_at", now),
        updated_at=kwargs.get("updated_at", now),
    )


def _make_auth_client(role: UserRole = UserRole.researcher) -> TestClient:
    app = create_app()
    fake_user = _make_user(role)
    app.dependency_overrides[get_current_user] = lambda: fake_user
    return TestClient(app, raise_server_exceptions=False)


def _make_no_auth_client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


STATION_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# POST /stations/{station_id}/foods
# ---------------------------------------------------------------------------

class TestAddFood:
    def test_adds_food_returns_201(self):
        sf = _make_sf_read(station_id=STATION_ID)
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.add_food", new=AsyncMock(return_value=sf)):
            r = client.post(f"/api/v1/stations/{STATION_ID}/foods", json={"food_id": str(uuid.uuid4())})
        assert r.status_code == 201
        assert r.json()["food_name"] == "Mixed Seeds"

    def test_station_not_found_returns_404(self):
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.add_food", new=AsyncMock(side_effect=StationNotFoundError())):
            r = client.post(f"/api/v1/stations/{STATION_ID}/foods", json={"food_id": str(uuid.uuid4())})
        assert r.status_code == 404

    def test_food_not_found_returns_404(self):
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.add_food", new=AsyncMock(side_effect=FoodNotFoundError())):
            r = client.post(f"/api/v1/stations/{STATION_ID}/foods", json={"food_id": str(uuid.uuid4())})
        assert r.status_code == 404

    def test_food_already_associated_returns_409(self):
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.add_food", new=AsyncMock(side_effect=FoodAlreadyAssociatedError())):
            r = client.post(f"/api/v1/stations/{STATION_ID}/foods", json={"food_id": str(uuid.uuid4())})
        assert r.status_code == 409
        assert r.json()["error"] == "FOOD_ALREADY_ASSOCIATED"

    def test_non_owner_returns_403(self):
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.add_food", new=AsyncMock(side_effect=StationFoodAccessDeniedError())):
            r = client.post(f"/api/v1/stations/{STATION_ID}/foods", json={"food_id": str(uuid.uuid4())})
        assert r.status_code == 403

    def test_unauthenticated_returns_401(self):
        client = _make_no_auth_client()
        r = client.post(f"/api/v1/stations/{STATION_ID}/foods", json={"food_id": str(uuid.uuid4())})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /stations/{station_id}/foods
# ---------------------------------------------------------------------------

class TestListStationFoods:
    def test_returns_200_with_list(self):
        items = [_make_sf_read(), _make_sf_read(active=False)]
        response = StationFoodListResponse(total=2, page=1, page_size=20, pages=1, items=items)
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.list_station_foods", new=AsyncMock(return_value=response)):
            r = client.get(f"/api/v1/stations/{STATION_ID}/foods")
        assert r.status_code == 200
        assert r.json()["total"] == 2

    def test_station_not_found_returns_404(self):
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.list_station_foods", new=AsyncMock(side_effect=StationNotFoundError())):
            r = client.get(f"/api/v1/stations/{STATION_ID}/foods")
        assert r.status_code == 404

    def test_non_member_returns_403(self):
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.list_station_foods", new=AsyncMock(side_effect=StationFoodAccessDeniedError())):
            r = client.get(f"/api/v1/stations/{STATION_ID}/foods")
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /stations/{station_id}/foods/{sf_id}/activate
# ---------------------------------------------------------------------------

class TestActivateFood:
    def test_activates_food_returns_200(self):
        sf = _make_sf_read(active=True)
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.activate_station_food", new=AsyncMock(return_value=sf)):
            r = client.patch(f"/api/v1/stations/{STATION_ID}/foods/{uuid.uuid4()}/activate")
        assert r.status_code == 200
        assert r.json()["active"] is True

    def test_not_found_returns_404(self):
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.activate_station_food", new=AsyncMock(side_effect=StationFoodNotFoundError())):
            r = client.patch(f"/api/v1/stations/{STATION_ID}/foods/{uuid.uuid4()}/activate")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /stations/{station_id}/foods/{sf_id}/deactivate
# ---------------------------------------------------------------------------

class TestDeactivateFood:
    def test_deactivates_food_returns_200(self):
        sf = _make_sf_read(active=False)
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.deactivate_station_food", new=AsyncMock(return_value=sf)):
            r = client.patch(f"/api/v1/stations/{STATION_ID}/foods/{uuid.uuid4()}/deactivate")
        assert r.status_code == 200
        assert r.json()["active"] is False

    def test_not_found_returns_404(self):
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.deactivate_station_food", new=AsyncMock(side_effect=StationFoodNotFoundError())):
            r = client.patch(f"/api/v1/stations/{STATION_ID}/foods/{uuid.uuid4()}/deactivate")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /stations/{station_id}/foods/{sf_id}
# ---------------------------------------------------------------------------

class TestRemoveFood:
    def test_removes_inactive_food_returns_204(self):
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.remove_station_food", new=AsyncMock()):
            r = client.delete(f"/api/v1/stations/{STATION_ID}/foods/{uuid.uuid4()}")
        assert r.status_code == 204

    def test_cannot_remove_active_food_returns_400(self):
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.remove_station_food", new=AsyncMock(side_effect=CannotRemoveActiveFoodError())):
            r = client.delete(f"/api/v1/stations/{STATION_ID}/foods/{uuid.uuid4()}")
        assert r.status_code == 400
        assert r.json()["error"] == "CANNOT_REMOVE_ACTIVE"

    def test_not_found_returns_404(self):
        client = _make_auth_client()
        with patch("modules.station_foods.router.StationFoodService.remove_station_food", new=AsyncMock(side_effect=StationFoodNotFoundError())):
            r = client.delete(f"/api/v1/stations/{STATION_ID}/foods/{uuid.uuid4()}")
        assert r.status_code == 404
