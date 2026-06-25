import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, require_researcher_or_above
from app.main import create_app
from modules.stations.schemas import StationListResponse, StationRead
from shared.enums import StationStatus, UserRole


def _make_user(role: UserRole) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = role
    user.is_active = True
    return user


def _make_station_read(**kwargs) -> StationRead:
    return StationRead(
        id=kwargs.get("id", uuid.uuid4()),
        code=kwargs.get("code", "STA-001"),
        name=kwargs.get("name", "Test Station"),
        zone_id=kwargs.get("zone_id", uuid.uuid4()),
        latitude=kwargs.get("latitude", 4.5),
        longitude=kwargs.get("longitude", -74.1),
        status=kwargs.get("status", StationStatus.active),
        created_at=kwargs.get("created_at", datetime.now(timezone.utc)),
        updated_at=kwargs.get("updated_at", datetime.now(timezone.utc)),
    )


def _station_payload(**overrides) -> dict:
    return {
        "code": "STA-001",
        "name": "Test Station",
        "zone_id": str(uuid.uuid4()),
        "latitude": 4.5,
        "longitude": -74.1,
        **overrides,
    }


def _make_client(role: UserRole) -> TestClient:
    app = create_app()
    fake_user = _make_user(role)
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[require_researcher_or_above] = lambda: fake_user
    return TestClient(app, raise_server_exceptions=False)


def _make_client_no_auth() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /api/v1/stations
# ---------------------------------------------------------------------------

class TestCreateStation:
    def test_researcher_can_create(self):
        station = _make_station_read()
        with patch("modules.stations.router.StationService.create_station", new=AsyncMock(return_value=station)):
            response = _make_client(UserRole.researcher).post("/api/v1/stations", json=_station_payload())
        assert response.status_code == 201
        body = response.json()
        assert body["code"] == "STA-001"

    def test_admin_can_create(self):
        station = _make_station_read()
        with patch("modules.stations.router.StationService.create_station", new=AsyncMock(return_value=station)):
            response = _make_client(UserRole.admin).post("/api/v1/stations", json=_station_payload())
        assert response.status_code == 201

    def test_field_operator_cannot_create(self):
        app = create_app()
        fake_user = _make_user(UserRole.field_operator)
        app.dependency_overrides[get_current_user] = lambda: fake_user
        from shared.base_exception import ForbiddenError
        app.dependency_overrides[require_researcher_or_above] = lambda: (_ for _ in ()).throw(ForbiddenError())
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/v1/stations", json=_station_payload())
        assert response.status_code == 403

    def test_returns_401_without_auth(self):
        response = _make_client_no_auth().post("/api/v1/stations", json=_station_payload())
        assert response.status_code == 401

    def test_returns_404_when_zone_not_found(self):
        from modules.zones.exceptions import ZoneNotFoundError
        with patch("modules.stations.router.StationService.create_station", new=AsyncMock(side_effect=ZoneNotFoundError())):
            response = _make_client(UserRole.researcher).post("/api/v1/stations", json=_station_payload())
        assert response.status_code == 404

    def test_returns_409_on_code_conflict(self):
        from modules.stations.exceptions import StationCodeConflictError
        with patch("modules.stations.router.StationService.create_station", new=AsyncMock(side_effect=StationCodeConflictError())):
            response = _make_client(UserRole.researcher).post("/api/v1/stations", json=_station_payload())
        assert response.status_code == 409
        assert response.json()["error"] == "STATION_CODE_EXISTS"

    def test_returns_422_on_invalid_code(self):
        response = _make_client(UserRole.researcher).post(
            "/api/v1/stations", json=_station_payload(code="invalid code!")
        )
        assert response.status_code == 422

    def test_returns_422_on_invalid_latitude(self):
        response = _make_client(UserRole.researcher).post(
            "/api/v1/stations", json=_station_payload(latitude=999.0)
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/stations
# ---------------------------------------------------------------------------

class TestListStations:
    def test_returns_200_for_any_authenticated_user(self):
        paginated = StationListResponse(items=[], total=0, page=1, page_size=20, pages=0)
        with patch("modules.stations.router.StationService.list_stations", new=AsyncMock(return_value=paginated)):
            response = _make_client(UserRole.field_operator).get("/api/v1/stations")
        assert response.status_code == 200

    def test_returns_401_without_auth(self):
        response = _make_client_no_auth().get("/api/v1/stations")
        assert response.status_code == 401

    def test_returns_paginated_response(self):
        station = _make_station_read()
        paginated = StationListResponse(items=[station], total=1, page=1, page_size=20, pages=1)
        with patch("modules.stations.router.StationService.list_stations", new=AsyncMock(return_value=paginated)):
            response = _make_client(UserRole.researcher).get("/api/v1/stations")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1

    def test_zone_id_filter_passed_to_service(self):
        zone_id = str(uuid.uuid4())
        paginated = StationListResponse(items=[], total=0, page=1, page_size=20, pages=0)
        with patch(
            "modules.stations.router.StationService.list_stations",
            new=AsyncMock(return_value=paginated),
        ) as mock_svc:
            _make_client(UserRole.researcher).get(f"/api/v1/stations?zone_id={zone_id}")
        _, kwargs = mock_svc.call_args
        assert str(kwargs.get("zone_id")) == zone_id

    def test_status_filter_passed_to_service(self):
        paginated = StationListResponse(items=[], total=0, page=1, page_size=20, pages=0)
        with patch(
            "modules.stations.router.StationService.list_stations",
            new=AsyncMock(return_value=paginated),
        ) as mock_svc:
            _make_client(UserRole.researcher).get("/api/v1/stations?status=inactive")
        _, kwargs = mock_svc.call_args
        assert kwargs.get("status") == StationStatus.inactive


# ---------------------------------------------------------------------------
# GET /api/v1/stations/{id}
# ---------------------------------------------------------------------------

class TestGetStation:
    def test_returns_200_when_found(self):
        station = _make_station_read()
        with patch("modules.stations.router.StationService.get_station", new=AsyncMock(return_value=station)):
            response = _make_client(UserRole.researcher).get(f"/api/v1/stations/{station.id}")
        assert response.status_code == 200
        assert response.json()["code"] == "STA-001"

    def test_returns_404_when_not_found(self):
        from modules.stations.exceptions import StationNotFoundError
        with patch("modules.stations.router.StationService.get_station", new=AsyncMock(side_effect=StationNotFoundError())):
            response = _make_client(UserRole.researcher).get(f"/api/v1/stations/{uuid.uuid4()}")
        assert response.status_code == 404
        assert response.json()["error"] == "NOT_FOUND"

    def test_returns_403_when_not_member(self):
        from modules.stations.exceptions import StationAccessDeniedError
        with patch("modules.stations.router.StationService.get_station", new=AsyncMock(side_effect=StationAccessDeniedError())):
            response = _make_client(UserRole.researcher).get(f"/api/v1/stations/{uuid.uuid4()}")
        assert response.status_code == 403

    def test_returns_401_without_auth(self):
        response = _make_client_no_auth().get(f"/api/v1/stations/{uuid.uuid4()}")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/v1/stations/{id}
# ---------------------------------------------------------------------------

class TestUpdateStation:
    def test_returns_200_on_success(self):
        station = _make_station_read(name="Updated")
        with patch("modules.stations.router.StationService.update_station", new=AsyncMock(return_value=station)):
            response = _make_client(UserRole.researcher).patch(
                f"/api/v1/stations/{station.id}", json={"name": "Updated"}
            )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"

    def test_returns_404_when_not_found(self):
        from modules.stations.exceptions import StationNotFoundError
        with patch("modules.stations.router.StationService.update_station", new=AsyncMock(side_effect=StationNotFoundError())):
            response = _make_client(UserRole.admin).patch(
                f"/api/v1/stations/{uuid.uuid4()}", json={"name": "Updated Station"}
            )
        assert response.status_code == 404

    def test_returns_403_when_not_owner(self):
        from modules.stations.exceptions import StationAccessDeniedError
        with patch("modules.stations.router.StationService.update_station", new=AsyncMock(side_effect=StationAccessDeniedError())):
            response = _make_client(UserRole.researcher).patch(
                f"/api/v1/stations/{uuid.uuid4()}", json={"name": "Updated Station"}
            )
        assert response.status_code == 403

    def test_returns_401_without_auth(self):
        response = _make_client_no_auth().patch(
            f"/api/v1/stations/{uuid.uuid4()}", json={"name": "Updated Station"}
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/v1/stations/{id}
# ---------------------------------------------------------------------------

class TestDeleteStation:
    def test_returns_204_on_success(self):
        with patch("modules.stations.router.StationService.delete_station", new=AsyncMock(return_value=None)):
            response = _make_client(UserRole.researcher).delete(f"/api/v1/stations/{uuid.uuid4()}")
        assert response.status_code == 204

    def test_returns_404_when_not_found(self):
        from modules.stations.exceptions import StationNotFoundError
        with patch("modules.stations.router.StationService.delete_station", new=AsyncMock(side_effect=StationNotFoundError())):
            response = _make_client(UserRole.admin).delete(f"/api/v1/stations/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_returns_403_when_not_owner(self):
        from modules.stations.exceptions import StationAccessDeniedError
        with patch("modules.stations.router.StationService.delete_station", new=AsyncMock(side_effect=StationAccessDeniedError())):
            response = _make_client(UserRole.researcher).delete(f"/api/v1/stations/{uuid.uuid4()}")
        assert response.status_code == 403

    def test_returns_401_without_auth(self):
        response = _make_client_no_auth().delete(f"/api/v1/stations/{uuid.uuid4()}")
        assert response.status_code == 401
