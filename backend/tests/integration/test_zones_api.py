import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, require_admin, require_researcher_or_above
from app.main import create_app
from modules.zones.schemas import ZoneListResponse, ZoneRead
from shared.enums import UserRole


def _make_user(role: UserRole) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Test User"
    user.email = "test@example.com"
    user.role = role
    user.is_active = True
    return user


def _make_zone_read(**kwargs) -> ZoneRead:
    return ZoneRead(
        id=kwargs.get("id", uuid.uuid4()),
        name=kwargs.get("name", "Zona Norte"),
        municipality=kwargs.get("municipality", "Municipio"),
        city=kwargs.get("city", "Bogotá"),
        country=kwargs.get("country", "CO"),
        altitude=kwargs.get("altitude", 2600.0),
        latitude=kwargs.get("latitude", 4.6),
        longitude=kwargs.get("longitude", -74.08),
        color=kwargs.get("color", "#52b788"),
        created_at=kwargs.get("created_at", datetime.now(timezone.utc)),
        updated_at=kwargs.get("updated_at", datetime.now(timezone.utc)),
    )


def _zone_payload(**overrides):
    return {
        "name": "Zona Norte",
        "municipality": "Municipio",
        "city": "Bogotá",
        "country": "CO",
        "altitude": 2600.0,
        "latitude": 4.6,
        "longitude": -74.08,
        **overrides,
    }


def _make_client(role: UserRole) -> TestClient:
    app = create_app()
    fake_user = _make_user(role)
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[require_researcher_or_above] = lambda: fake_user
    app.dependency_overrides[require_admin] = lambda: fake_user
    return TestClient(app, raise_server_exceptions=False)


def _make_client_no_auth() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /api/v1/zones
# ---------------------------------------------------------------------------

class TestListZones:
    def test_returns_200_for_authenticated_user(self):
        zone = _make_zone_read()
        paginated = ZoneListResponse(items=[zone], total=1, page=1, page_size=20, pages=1)
        with patch(
            "modules.zones.router.ZoneService.list_zones",
            new=AsyncMock(return_value=paginated),
        ):
            response = _make_client(UserRole.researcher).get("/api/v1/zones")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1

    def test_returns_401_without_auth(self):
        response = _make_client_no_auth().get("/api/v1/zones")
        assert response.status_code == 401

    def test_returns_200_for_field_operator(self):
        paginated = ZoneListResponse(items=[], total=0, page=1, page_size=20, pages=0)
        with patch(
            "modules.zones.router.ZoneService.list_zones",
            new=AsyncMock(return_value=paginated),
        ):
            response = _make_client(UserRole.field_operator).get("/api/v1/zones")
        assert response.status_code == 200

    def test_country_filter_is_passed_to_service(self):
        paginated = ZoneListResponse(items=[], total=0, page=1, page_size=20, pages=0)
        with patch(
            "modules.zones.router.ZoneService.list_zones",
            new=AsyncMock(return_value=paginated),
        ) as mock_svc:
            response = _make_client(UserRole.researcher).get("/api/v1/zones?country=Colombia")
        assert response.status_code == 200
        _, kwargs = mock_svc.call_args
        assert kwargs.get("country") == "Colombia"


# ---------------------------------------------------------------------------
# GET /api/v1/zones/{zone_id}
# ---------------------------------------------------------------------------

class TestGetZone:
    def test_returns_200_when_found(self):
        zone = _make_zone_read()
        with patch(
            "modules.zones.router.ZoneService.get_zone",
            new=AsyncMock(return_value=zone),
        ):
            response = _make_client(UserRole.researcher).get(f"/api/v1/zones/{zone.id}")
        assert response.status_code == 200
        assert response.json()["name"] == zone.name

    def test_returns_404_when_not_found(self):
        from modules.zones.exceptions import ZoneNotFoundError
        with patch(
            "modules.zones.router.ZoneService.get_zone",
            new=AsyncMock(side_effect=ZoneNotFoundError()),
        ):
            response = _make_client(UserRole.researcher).get(f"/api/v1/zones/{uuid.uuid4()}")
        assert response.status_code == 404
        assert response.json()["error"] == "ZONE_NOT_FOUND"

    def test_returns_401_without_auth(self):
        response = _make_client_no_auth().get(f"/api/v1/zones/{uuid.uuid4()}")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/zones
# ---------------------------------------------------------------------------

class TestCreateZone:
    def test_admin_can_create_zone(self):
        zone = _make_zone_read()
        with patch(
            "modules.zones.router.ZoneService.create_zone",
            new=AsyncMock(return_value=zone),
        ):
            response = _make_client(UserRole.admin).post("/api/v1/zones", json=_zone_payload())
        assert response.status_code == 201

    def test_researcher_can_create_zone(self):
        zone = _make_zone_read()
        with patch(
            "modules.zones.router.ZoneService.create_zone",
            new=AsyncMock(return_value=zone),
        ):
            response = _make_client(UserRole.researcher).post("/api/v1/zones", json=_zone_payload())
        assert response.status_code == 201

    def test_returns_409_on_name_conflict(self):
        from modules.zones.exceptions import ZoneNameConflictError
        with patch(
            "modules.zones.router.ZoneService.create_zone",
            new=AsyncMock(side_effect=ZoneNameConflictError()),
        ):
            response = _make_client(UserRole.admin).post("/api/v1/zones", json=_zone_payload())
        assert response.status_code == 409
        assert response.json()["error"] == "ZONE_NAME_EXISTS"

    def test_returns_422_on_invalid_latitude(self):
        response = _make_client(UserRole.admin).post(
            "/api/v1/zones", json=_zone_payload(latitude=999.0)
        )
        assert response.status_code == 422

    def test_field_operator_cannot_create_zone(self):
        app = create_app()
        fake_user = _make_user(UserRole.field_operator)
        app.dependency_overrides[get_current_user] = lambda: fake_user
        from shared.base_exception import ForbiddenError
        app.dependency_overrides[require_researcher_or_above] = lambda: (_ for _ in ()).throw(ForbiddenError())
        client = TestClient(app, raise_server_exceptions=False)
        with patch(
            "modules.zones.router.ZoneService.create_zone",
            new=AsyncMock(return_value=_make_zone_read()),
        ):
            response = client.post("/api/v1/zones", json=_zone_payload())
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/v1/zones/{zone_id}
# ---------------------------------------------------------------------------

class TestUpdateZone:
    def test_admin_can_update_zone(self):
        zone = _make_zone_read(name="Updated Zone")
        with patch(
            "modules.zones.router.ZoneService.update_zone",
            new=AsyncMock(return_value=zone),
        ):
            response = _make_client(UserRole.admin).patch(
                f"/api/v1/zones/{zone.id}", json={"name": "Updated Zone"}
            )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Zone"

    def test_researcher_can_update_zone(self):
        zone = _make_zone_read(name="Updated Zone")
        with patch(
            "modules.zones.router.ZoneService.update_zone",
            new=AsyncMock(return_value=zone),
        ):
            response = _make_client(UserRole.researcher).patch(
                f"/api/v1/zones/{zone.id}", json={"name": "Updated Zone"}
            )
        assert response.status_code == 200

    def test_returns_404_on_missing_zone(self):
        from modules.zones.exceptions import ZoneNotFoundError
        with patch(
            "modules.zones.router.ZoneService.update_zone",
            new=AsyncMock(side_effect=ZoneNotFoundError()),
        ):
            response = _make_client(UserRole.admin).patch(
                f"/api/v1/zones/{uuid.uuid4()}", json={"name": "Xy"}
            )
        assert response.status_code == 404

    def test_field_operator_cannot_update_zone(self):
        app = create_app()
        fake_user = _make_user(UserRole.field_operator)
        app.dependency_overrides[get_current_user] = lambda: fake_user
        from shared.base_exception import ForbiddenError
        app.dependency_overrides[require_researcher_or_above] = lambda: (_ for _ in ()).throw(ForbiddenError())
        client = TestClient(app, raise_server_exceptions=False)
        with patch(
            "modules.zones.router.ZoneService.update_zone",
            new=AsyncMock(return_value=_make_zone_read()),
        ):
            response = client.patch(f"/api/v1/zones/{uuid.uuid4()}", json={"name": "X"})
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /api/v1/zones/{zone_id}
# ---------------------------------------------------------------------------

class TestDeleteZone:
    def test_admin_can_delete_zone(self):
        with patch(
            "modules.zones.router.ZoneService.delete_zone",
            new=AsyncMock(return_value=None),
        ):
            response = _make_client(UserRole.admin).delete(f"/api/v1/zones/{uuid.uuid4()}")
        assert response.status_code == 204

    def test_returns_404_on_missing_zone(self):
        from modules.zones.exceptions import ZoneNotFoundError
        with patch(
            "modules.zones.router.ZoneService.delete_zone",
            new=AsyncMock(side_effect=ZoneNotFoundError()),
        ):
            response = _make_client(UserRole.admin).delete(f"/api/v1/zones/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_returns_400_when_zone_has_active_stations(self):
        from modules.zones.exceptions import ZoneHasActiveStationsError
        with patch(
            "modules.zones.router.ZoneService.delete_zone",
            new=AsyncMock(side_effect=ZoneHasActiveStationsError()),
        ):
            response = _make_client(UserRole.admin).delete(f"/api/v1/zones/{uuid.uuid4()}")
        assert response.status_code == 400
        assert response.json()["error"] == "ZONE_HAS_STATIONS"

    def test_researcher_cannot_delete_zone(self):
        app = create_app()
        fake_user = _make_user(UserRole.researcher)
        app.dependency_overrides[get_current_user] = lambda: fake_user
        from shared.base_exception import ForbiddenError
        app.dependency_overrides[require_admin] = lambda: (_ for _ in ()).throw(ForbiddenError())
        client = TestClient(app, raise_server_exceptions=False)
        with patch(
            "modules.zones.router.ZoneService.delete_zone",
            new=AsyncMock(return_value=None),
        ):
            response = client.delete(f"/api/v1/zones/{uuid.uuid4()}")
        assert response.status_code == 403

    def test_field_operator_cannot_delete_zone(self):
        app = create_app()
        fake_user = _make_user(UserRole.field_operator)
        app.dependency_overrides[get_current_user] = lambda: fake_user
        from shared.base_exception import ForbiddenError
        app.dependency_overrides[require_admin] = lambda: (_ for _ in ()).throw(ForbiddenError())
        client = TestClient(app, raise_server_exceptions=False)
        with patch(
            "modules.zones.router.ZoneService.delete_zone",
            new=AsyncMock(return_value=None),
        ):
            response = client.delete(f"/api/v1/zones/{uuid.uuid4()}")
        assert response.status_code == 403

    def test_returns_401_without_auth(self):
        response = _make_client_no_auth().delete(f"/api/v1/zones/{uuid.uuid4()}")
        assert response.status_code == 401
