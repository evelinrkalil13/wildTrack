import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import create_app
from modules.geoportal.schemas import GeoportalStationRead
from shared.enums import DeviceStatus, StationStatus, UserRole


def _make_user(role: UserRole) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = role
    user.is_active = True
    return user


def _make_station_read(**kwargs) -> GeoportalStationRead:
    return GeoportalStationRead(
        station_id=str(kwargs.get("station_id", uuid.uuid4())),
        station_code=kwargs.get("station_code", "STA-001"),
        station_name=kwargs.get("station_name", "Comedero Norte"),
        status=kwargs.get("status", StationStatus.active),
        latitude=kwargs.get("latitude", 4.71),
        longitude=kwargs.get("longitude", -74.07),
        zone_id=str(kwargs.get("zone_id", uuid.uuid4())),
        zone_name=kwargs.get("zone_name", "Zona Norte"),
        device=None,
        latest_telemetry=None,
        recent_events=[],
        open_alerts_count=0,
    )


def _make_auth_client(role: UserRole = UserRole.researcher) -> TestClient:
    app = create_app()
    fake_user = _make_user(role)
    app.dependency_overrides[get_current_user] = lambda: fake_user
    return TestClient(app, raise_server_exceptions=False)


def _make_no_auth_client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


class TestListGeoportalStations:
    def test_requires_authentication(self):
        client = _make_no_auth_client()
        res = client.get("/api/v1/geoportal/stations")
        assert res.status_code == 401

    def test_returns_empty_list_when_no_stations(self):
        client = _make_auth_client(UserRole.researcher)
        with patch(
            "modules.geoportal.router.GeoportalService.list_stations",
            new=AsyncMock(return_value=[]),
        ):
            res = client.get("/api/v1/geoportal/stations")

        assert res.status_code == 200
        assert res.json() == []

    def test_returns_station_list(self):
        client = _make_auth_client(UserRole.admin)
        station = _make_station_read()
        with patch(
            "modules.geoportal.router.GeoportalService.list_stations",
            new=AsyncMock(return_value=[station]),
        ):
            res = client.get("/api/v1/geoportal/stations")

        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["station_code"] == "STA-001"
        assert data[0]["zone_name"] == "Zona Norte"
        assert data[0]["device"] is None
        assert data[0]["latest_telemetry"] is None
        assert data[0]["recent_events"] == []
        assert data[0]["open_alerts_count"] == 0

    def test_field_operator_can_access(self):
        client = _make_auth_client(UserRole.field_operator)
        with patch(
            "modules.geoportal.router.GeoportalService.list_stations",
            new=AsyncMock(return_value=[]),
        ):
            res = client.get("/api/v1/geoportal/stations")

        assert res.status_code == 200
