import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, require_admin
from app.main import create_app
from modules.devices.schemas import DeviceAssignRead, DeviceListResponse, DeviceRead
from shared.enums import DeviceStatus, UserRole


def _make_user(role: UserRole) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = role
    user.is_active = True
    return user


def _make_device_read(**kwargs) -> DeviceRead:
    now = datetime.now(timezone.utc)
    return DeviceRead(
        id=kwargs.get("id", uuid.uuid4()),
        serial_number=kwargs.get("serial_number", "WT-ESP32-0001"),
        name=kwargs.get("name", "Feeder Alpha"),
        mac_address=kwargs.get("mac_address", None),
        station_id=kwargs.get("station_id", None),
        station_code=kwargs.get("station_code", None),
        status=kwargs.get("status", DeviceStatus.unassigned),
        firmware_version=kwargs.get("firmware_version", None),
        last_seen=kwargs.get("last_seen", None),
        created_at=kwargs.get("created_at", now),
        updated_at=kwargs.get("updated_at", now),
    )


def _make_assign_read(**kwargs) -> DeviceAssignRead:
    now = datetime.now(timezone.utc)
    return DeviceAssignRead(
        id=kwargs.get("id", uuid.uuid4()),
        station_id=kwargs.get("station_id", None),
        status=kwargs.get("status", DeviceStatus.unassigned),
        updated_at=kwargs.get("updated_at", now),
    )


def _device_payload(**overrides) -> dict:
    return {"serial_number": "WT-ESP32-0001", "name": "Feeder Alpha", **overrides}


def _make_admin_client() -> TestClient:
    app = create_app()
    fake_user = _make_user(UserRole.admin)
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[require_admin] = lambda: fake_user
    return TestClient(app, raise_server_exceptions=False)


def _make_researcher_client() -> TestClient:
    app = create_app()
    fake_user = _make_user(UserRole.researcher)
    app.dependency_overrides[get_current_user] = lambda: fake_user
    # require_admin is NOT overridden — will raise 403
    return TestClient(app, raise_server_exceptions=False)


def _make_no_auth_client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /api/v1/devices
# ---------------------------------------------------------------------------

class TestCreateDevice:
    def test_admin_can_create(self):
        device = _make_device_read()
        with patch("modules.devices.router.DeviceService.create_device", new=AsyncMock(return_value=device)):
            response = _make_admin_client().post("/api/v1/devices", json=_device_payload())
        assert response.status_code == 201
        assert response.json()["serial_number"] == "WT-ESP32-0001"
        assert response.json()["status"] == "unassigned"

    def test_returns_401_without_auth(self):
        response = _make_no_auth_client().post("/api/v1/devices", json=_device_payload())
        assert response.status_code == 401

    def test_non_admin_gets_403(self):
        response = _make_researcher_client().post("/api/v1/devices", json=_device_payload())
        assert response.status_code == 403

    def test_returns_409_on_serial_conflict(self):
        from modules.devices.exceptions import SerialNumberConflictError
        with patch(
            "modules.devices.router.DeviceService.create_device",
            new=AsyncMock(side_effect=SerialNumberConflictError()),
        ):
            response = _make_admin_client().post("/api/v1/devices", json=_device_payload())
        assert response.status_code == 409
        assert response.json()["error"] == "SERIAL_EXISTS"

    def test_returns_422_on_short_serial(self):
        response = _make_admin_client().post("/api/v1/devices", json=_device_payload(serial_number="AB"))
        assert response.status_code == 422

    def test_returns_422_on_invalid_mac_address(self):
        response = _make_admin_client().post(
            "/api/v1/devices", json=_device_payload(mac_address="not-a-mac")
        )
        assert response.status_code == 422

    def test_valid_mac_address_accepted(self):
        device = _make_device_read(mac_address="AA:BB:CC:DD:EE:FF")
        with patch("modules.devices.router.DeviceService.create_device", new=AsyncMock(return_value=device)):
            response = _make_admin_client().post(
                "/api/v1/devices",
                json=_device_payload(mac_address="AA:BB:CC:DD:EE:FF"),
            )
        assert response.status_code == 201
        assert response.json()["mac_address"] == "AA:BB:CC:DD:EE:FF"


# ---------------------------------------------------------------------------
# GET /api/v1/devices
# ---------------------------------------------------------------------------

class TestListDevices:
    def test_any_authenticated_user_can_list(self):
        paginated = DeviceListResponse(items=[], total=0, page=1, page_size=20, pages=0)
        with patch("modules.devices.router.DeviceService.list_devices", new=AsyncMock(return_value=paginated)):
            response = _make_researcher_client().get("/api/v1/devices")
        assert response.status_code == 200

    def test_returns_401_without_auth(self):
        response = _make_no_auth_client().get("/api/v1/devices")
        assert response.status_code == 401

    def test_returns_paginated_response(self):
        device = _make_device_read()
        paginated = DeviceListResponse(items=[device], total=1, page=1, page_size=20, pages=1)
        with patch("modules.devices.router.DeviceService.list_devices", new=AsyncMock(return_value=paginated)):
            response = _make_admin_client().get("/api/v1/devices")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1

    def test_status_filter_passed_to_service(self):
        paginated = DeviceListResponse(items=[], total=0, page=1, page_size=20, pages=0)
        with patch(
            "modules.devices.router.DeviceService.list_devices",
            new=AsyncMock(return_value=paginated),
        ) as mock_svc:
            _make_admin_client().get("/api/v1/devices?status=online")
        _, kwargs = mock_svc.call_args
        assert kwargs.get("status") == DeviceStatus.online

    def test_station_id_filter_passed_to_service(self):
        station_id = str(uuid.uuid4())
        paginated = DeviceListResponse(items=[], total=0, page=1, page_size=20, pages=0)
        with patch(
            "modules.devices.router.DeviceService.list_devices",
            new=AsyncMock(return_value=paginated),
        ) as mock_svc:
            _make_admin_client().get(f"/api/v1/devices?station_id={station_id}")
        _, kwargs = mock_svc.call_args
        assert str(kwargs.get("station_id")) == station_id


# ---------------------------------------------------------------------------
# GET /api/v1/devices/{id}
# ---------------------------------------------------------------------------

class TestGetDevice:
    def test_returns_200_when_found(self):
        device = _make_device_read()
        with patch("modules.devices.router.DeviceService.get_device", new=AsyncMock(return_value=device)):
            response = _make_admin_client().get(f"/api/v1/devices/{device.id}")
        assert response.status_code == 200
        assert response.json()["serial_number"] == "WT-ESP32-0001"

    def test_returns_404_when_not_found(self):
        from modules.devices.exceptions import DeviceNotFoundError
        with patch(
            "modules.devices.router.DeviceService.get_device",
            new=AsyncMock(side_effect=DeviceNotFoundError()),
        ):
            response = _make_admin_client().get(f"/api/v1/devices/{uuid.uuid4()}")
        assert response.status_code == 404
        assert response.json()["error"] == "NOT_FOUND"

    def test_returns_403_when_access_denied(self):
        from modules.devices.exceptions import DeviceAccessDeniedError
        with patch(
            "modules.devices.router.DeviceService.get_device",
            new=AsyncMock(side_effect=DeviceAccessDeniedError()),
        ):
            response = _make_researcher_client().get(f"/api/v1/devices/{uuid.uuid4()}")
        assert response.status_code == 403

    def test_returns_401_without_auth(self):
        response = _make_no_auth_client().get(f"/api/v1/devices/{uuid.uuid4()}")
        assert response.status_code == 401

    def test_response_includes_station_code(self):
        station_id = uuid.uuid4()
        device = _make_device_read(station_id=station_id, station_code="STA-001", status=DeviceStatus.online)
        with patch("modules.devices.router.DeviceService.get_device", new=AsyncMock(return_value=device)):
            response = _make_admin_client().get(f"/api/v1/devices/{device.id}")
        assert response.json()["station_code"] == "STA-001"
        assert response.json()["station_id"] == str(station_id)


# ---------------------------------------------------------------------------
# PATCH /api/v1/devices/{id}
# ---------------------------------------------------------------------------

class TestUpdateDevice:
    def test_admin_can_update_name(self):
        device = _make_device_read(name="Updated Name")
        with patch("modules.devices.router.DeviceService.update_device", new=AsyncMock(return_value=device)):
            response = _make_admin_client().patch(
                f"/api/v1/devices/{device.id}", json={"name": "Updated Name"}
            )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_non_admin_gets_403(self):
        response = _make_researcher_client().patch(
            f"/api/v1/devices/{uuid.uuid4()}", json={"name": "X"}
        )
        assert response.status_code == 403

    def test_returns_404_when_not_found(self):
        from modules.devices.exceptions import DeviceNotFoundError
        with patch(
            "modules.devices.router.DeviceService.update_device",
            new=AsyncMock(side_effect=DeviceNotFoundError()),
        ):
            response = _make_admin_client().patch(
                f"/api/v1/devices/{uuid.uuid4()}", json={"name": "X"}
            )
        assert response.status_code == 404

    def test_returns_401_without_auth(self):
        response = _make_no_auth_client().patch(
            f"/api/v1/devices/{uuid.uuid4()}", json={"name": "X"}
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/v1/devices/{id}/assign
# ---------------------------------------------------------------------------

class TestAssignDevice:
    def test_admin_can_assign(self):
        station_id = uuid.uuid4()
        assign_read = _make_assign_read(station_id=station_id, status=DeviceStatus.online)
        with patch("modules.devices.router.DeviceService.assign_device", new=AsyncMock(return_value=assign_read)):
            response = _make_admin_client().patch(
                f"/api/v1/devices/{uuid.uuid4()}/assign",
                json={"station_id": str(station_id)},
            )
        assert response.status_code == 200
        assert response.json()["status"] == "online"
        assert response.json()["station_id"] == str(station_id)

    def test_non_admin_gets_403(self):
        response = _make_researcher_client().patch(
            f"/api/v1/devices/{uuid.uuid4()}/assign",
            json={"station_id": str(uuid.uuid4())},
        )
        assert response.status_code == 403

    def test_returns_400_on_already_assigned(self):
        from modules.devices.exceptions import DeviceAlreadyAssignedError
        with patch(
            "modules.devices.router.DeviceService.assign_device",
            new=AsyncMock(side_effect=DeviceAlreadyAssignedError()),
        ):
            response = _make_admin_client().patch(
                f"/api/v1/devices/{uuid.uuid4()}/assign",
                json={"station_id": str(uuid.uuid4())},
            )
        assert response.status_code == 400
        assert response.json()["error"] == "DEVICE_ALREADY_ASSIGNED"

    def test_returns_400_on_station_has_device(self):
        from modules.devices.exceptions import StationHasDeviceError
        with patch(
            "modules.devices.router.DeviceService.assign_device",
            new=AsyncMock(side_effect=StationHasDeviceError()),
        ):
            response = _make_admin_client().patch(
                f"/api/v1/devices/{uuid.uuid4()}/assign",
                json={"station_id": str(uuid.uuid4())},
            )
        assert response.status_code == 400
        assert response.json()["error"] == "STATION_HAS_DEVICE"

    def test_returns_404_on_station_not_found(self):
        from modules.stations.exceptions import StationNotFoundError
        with patch(
            "modules.devices.router.DeviceService.assign_device",
            new=AsyncMock(side_effect=StationNotFoundError()),
        ):
            response = _make_admin_client().patch(
                f"/api/v1/devices/{uuid.uuid4()}/assign",
                json={"station_id": str(uuid.uuid4())},
            )
        assert response.status_code == 404

    def test_returns_401_without_auth(self):
        response = _make_no_auth_client().patch(
            f"/api/v1/devices/{uuid.uuid4()}/assign",
            json={"station_id": str(uuid.uuid4())},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/v1/devices/{id}/unassign
# ---------------------------------------------------------------------------

class TestUnassignDevice:
    def test_admin_can_unassign(self):
        assign_read = _make_assign_read(station_id=None, status=DeviceStatus.unassigned)
        with patch("modules.devices.router.DeviceService.unassign_device", new=AsyncMock(return_value=assign_read)):
            response = _make_admin_client().patch(f"/api/v1/devices/{uuid.uuid4()}/unassign")
        assert response.status_code == 200
        assert response.json()["status"] == "unassigned"
        assert response.json()["station_id"] is None

    def test_non_admin_gets_403(self):
        response = _make_researcher_client().patch(f"/api/v1/devices/{uuid.uuid4()}/unassign")
        assert response.status_code == 403

    def test_returns_400_on_device_not_assigned(self):
        from modules.devices.exceptions import DeviceNotAssignedError
        with patch(
            "modules.devices.router.DeviceService.unassign_device",
            new=AsyncMock(side_effect=DeviceNotAssignedError()),
        ):
            response = _make_admin_client().patch(f"/api/v1/devices/{uuid.uuid4()}/unassign")
        assert response.status_code == 400
        assert response.json()["error"] == "DEVICE_NOT_ASSIGNED"

    def test_returns_401_without_auth(self):
        response = _make_no_auth_client().patch(f"/api/v1/devices/{uuid.uuid4()}/unassign")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/v1/devices/{id}
# ---------------------------------------------------------------------------

class TestDeleteDevice:
    def test_admin_can_delete(self):
        with patch("modules.devices.router.DeviceService.delete_device", new=AsyncMock(return_value=None)):
            response = _make_admin_client().delete(f"/api/v1/devices/{uuid.uuid4()}")
        assert response.status_code == 204

    def test_non_admin_gets_403(self):
        response = _make_researcher_client().delete(f"/api/v1/devices/{uuid.uuid4()}")
        assert response.status_code == 403

    def test_returns_404_when_not_found(self):
        from modules.devices.exceptions import DeviceNotFoundError
        with patch(
            "modules.devices.router.DeviceService.delete_device",
            new=AsyncMock(side_effect=DeviceNotFoundError()),
        ):
            response = _make_admin_client().delete(f"/api/v1/devices/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_returns_401_without_auth(self):
        response = _make_no_auth_client().delete(f"/api/v1/devices/{uuid.uuid4()}")
        assert response.status_code == 401
