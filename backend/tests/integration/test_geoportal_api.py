import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import create_app
from modules.geoportal.schemas import (
    ActivityItem,
    ActivityItemType,
    AnimalHistoryResponse,
    FeedingEvent,
    FeederRankItem,
    GeoportalAnimalRead,
    GeoportalStationDetail,
    GeoportalStationMapItem,
    GeoportalStatsResponse,
    StationEventDetail,
    StationEventsResponse,
    TraceStop,
)
from shared.enums import DeviceStatus, StationStatus, TimeFilter, UserRole


def _make_user(role: UserRole) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = role
    user.is_active = True
    return user


def _make_station_map_item(**kwargs) -> GeoportalStationMapItem:
    return GeoportalStationMapItem(
        station_id=str(kwargs.get("station_id", uuid.uuid4())),
        station_code=kwargs.get("station_code", "STA-001"),
        station_name=kwargs.get("station_name", "Comedero Norte"),
        status=kwargs.get("status", StationStatus.active),
        latitude=kwargs.get("latitude", 4.71),
        longitude=kwargs.get("longitude", -74.07),
        zone_id=str(kwargs.get("zone_id", uuid.uuid4())),
        zone_name=kwargs.get("zone_name", "Zona Norte"),
        zone_color=kwargs.get("zone_color", "#52b788"),
        device_status=kwargs.get("device_status", None),
        open_alerts_count=kwargs.get("open_alerts_count", 0),
        is_live=kwargs.get("is_live", False),
        visitas_total=kwargs.get("visitas_total", 0),
        visitas_identificadas=kwargs.get("visitas_identificadas", 0),
        visitas_sin_identificar=kwargs.get("visitas_sin_identificar", 0),
    )


def _make_station_detail(**kwargs) -> GeoportalStationDetail:
    return GeoportalStationDetail(
        station_id=str(kwargs.get("station_id", uuid.uuid4())),
        station_code=kwargs.get("station_code", "STA-001"),
        station_name=kwargs.get("station_name", "Comedero Norte"),
        status=kwargs.get("status", StationStatus.active),
        latitude=kwargs.get("latitude", 4.71),
        longitude=kwargs.get("longitude", -74.07),
        zone_id=str(kwargs.get("zone_id", uuid.uuid4())),
        zone_name=kwargs.get("zone_name", "Zona Norte"),
        zone_color=kwargs.get("zone_color", "#52b788"),
        device_status=kwargs.get("device_status", None),
        open_alerts_count=kwargs.get("open_alerts_count", 0),
        is_live=kwargs.get("is_live", False),
        visitas_total=kwargs.get("visitas_total", 0),
        visitas_identificadas=kwargs.get("visitas_identificadas", 0),
        visitas_sin_identificar=kwargs.get("visitas_sin_identificar", 0),
        food_type=kwargs.get("food_type", None),
        device=None,
        latest_telemetry=None,
        peso_promedio_g=kwargs.get("peso_promedio_g", None),
        peso_mediana_g=kwargs.get("peso_mediana_g", None),
        visitas_por_dia=kwargs.get("visitas_por_dia", [0] * 7),
        recent_events=[],
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

    def test_returns_lean_station_list(self):
        client = _make_auth_client(UserRole.admin)
        station = _make_station_map_item(visitas_total=12, is_live=True)
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
        assert data[0]["zone_color"] == "#52b788"
        assert data[0]["is_live"] is True
        assert data[0]["visitas_total"] == 12
        assert data[0]["open_alerts_count"] == 0
        # Detail fields must NOT be present in the lean list
        assert "device" not in data[0]
        assert "latest_telemetry" not in data[0]
        assert "recent_events" not in data[0]

    def test_accepts_time_filter_query_param(self):
        client = _make_auth_client(UserRole.researcher)
        with patch(
            "modules.geoportal.router.GeoportalService.list_stations",
            new=AsyncMock(return_value=[]),
        ) as mock:
            res = client.get("/api/v1/geoportal/stations?time_filter=24h")

        assert res.status_code == 200

    def test_field_operator_can_access(self):
        client = _make_auth_client(UserRole.field_operator)
        with patch(
            "modules.geoportal.router.GeoportalService.list_stations",
            new=AsyncMock(return_value=[]),
        ):
            res = client.get("/api/v1/geoportal/stations")

        assert res.status_code == 200


class TestGetGeoportalStationDetail:
    def test_requires_authentication(self):
        client = _make_no_auth_client()
        res = client.get(f"/api/v1/geoportal/stations/{uuid.uuid4()}")
        assert res.status_code == 401

    def test_returns_404_when_not_found(self):
        client = _make_auth_client(UserRole.researcher)
        with patch(
            "modules.geoportal.router.GeoportalService.get_station_detail",
            new=AsyncMock(return_value=None),
        ):
            res = client.get(f"/api/v1/geoportal/stations/{uuid.uuid4()}")

        assert res.status_code == 404

    def test_returns_detail_with_all_fields(self):
        client = _make_auth_client(UserRole.researcher)
        station_id = uuid.uuid4()
        detail = _make_station_detail(
            station_id=station_id,
            is_live=True,
            visitas_total=47,
            visitas_identificadas=32,
            visitas_sin_identificar=15,
            peso_promedio_g=248.0,
            peso_mediana_g=234.0,
            visitas_por_dia=[5, 8, 10, 7, 6, 6, 5],
        )
        with patch(
            "modules.geoportal.router.GeoportalService.get_station_detail",
            new=AsyncMock(return_value=detail),
        ):
            res = client.get(f"/api/v1/geoportal/stations/{station_id}")

        assert res.status_code == 200
        data = res.json()
        assert data["station_id"] == str(station_id)
        assert data["is_live"] is True
        assert data["visitas_total"] == 47
        assert data["visitas_identificadas"] == 32
        assert data["visitas_sin_identificar"] == 15
        assert data["peso_promedio_g"] == 248.0
        assert data["peso_mediana_g"] == 234.0
        assert data["visitas_por_dia"] == [5, 8, 10, 7, 6, 6, 5]
        assert "device" in data
        assert "latest_telemetry" in data
        assert "recent_events" in data

    def test_accepts_time_filter_param(self):
        client = _make_auth_client(UserRole.researcher)
        station_id = uuid.uuid4()
        detail = _make_station_detail(station_id=station_id)
        with patch(
            "modules.geoportal.router.GeoportalService.get_station_detail",
            new=AsyncMock(return_value=detail),
        ):
            res = client.get(f"/api/v1/geoportal/stations/{station_id}?time_filter=30d")

        assert res.status_code == 200


def _make_animal_read(**kwargs) -> GeoportalAnimalRead:
    return GeoportalAnimalRead(
        animal_id=str(kwargs.get("animal_id", uuid.uuid4())),
        rfid_tag=kwargs.get("rfid_tag", "RFID-001"),
        species=kwargs.get("species", "Cervidae"),
        sex=kwargs.get("sex", "female"),
        estimated_age=kwargs.get("estimated_age", None),
        notes=kwargs.get("notes", None),
        registered_at=kwargs.get("registered_at", datetime.now(timezone.utc)),
        total_visits=kwargs.get("total_visits", 0),
        last_visit=kwargs.get("last_visit", None),
        avg_consumed_g=kwargs.get("avg_consumed_g", None),
    )


def _make_activity_item(
    item_type: ActivityItemType = ActivityItemType.feeding,
    description: str = "Alimentación",
    **kwargs,
) -> ActivityItem:
    return ActivityItem(
        item_type=item_type,
        timestamp=kwargs.get("timestamp", datetime.now(timezone.utc)),
        description=description,
        rfid_tag=kwargs.get("rfid_tag", None),
        animal_species=kwargs.get("animal_species", None),
        media_urls=kwargs.get("media_urls", []),
        severity=kwargs.get("severity", None),
    )


class TestListStationAnimals:
    def test_requires_authentication(self):
        client = _make_no_auth_client()
        res = client.get(f"/api/v1/geoportal/stations/{uuid.uuid4()}/animals")
        assert res.status_code == 401

    def test_returns_empty_list_when_no_animals(self):
        client = _make_auth_client(UserRole.researcher)
        station_id = uuid.uuid4()
        with patch(
            "modules.geoportal.router.GeoportalService.list_station_animals",
            new=AsyncMock(return_value=[]),
        ):
            res = client.get(f"/api/v1/geoportal/stations/{station_id}/animals")

        assert res.status_code == 200
        assert res.json() == []

    def test_returns_animal_list_with_correct_schema(self):
        client = _make_auth_client(UserRole.researcher)
        station_id = uuid.uuid4()
        animals = [
            _make_animal_read(
                rfid_tag="RFID-001",
                species="Cervidae",
                sex="female",
                total_visits=15,
                avg_consumed_g=120.5,
            ),
            _make_animal_read(
                rfid_tag="RFID-002",
                species="Tayassuidae",
                sex="male",
                total_visits=7,
                avg_consumed_g=None,
            ),
        ]
        with patch(
            "modules.geoportal.router.GeoportalService.list_station_animals",
            new=AsyncMock(return_value=animals),
        ):
            res = client.get(f"/api/v1/geoportal/stations/{station_id}/animals")

        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        first = data[0]
        assert first["rfid_tag"] == "RFID-001"
        assert first["species"] == "Cervidae"
        assert first["total_visits"] == 15
        assert first["avg_consumed_g"] == 120.5
        second = data[1]
        assert second["avg_consumed_g"] is None

    def test_accepts_time_filter_query_param(self):
        client = _make_auth_client(UserRole.admin)
        station_id = uuid.uuid4()
        with patch(
            "modules.geoportal.router.GeoportalService.list_station_animals",
            new=AsyncMock(return_value=[]),
        ):
            res = client.get(
                f"/api/v1/geoportal/stations/{station_id}/animals?time_filter=30d"
            )

        assert res.status_code == 200

    def test_field_operator_can_access(self):
        client = _make_auth_client(UserRole.field_operator)
        station_id = uuid.uuid4()
        with patch(
            "modules.geoportal.router.GeoportalService.list_station_animals",
            new=AsyncMock(return_value=[]),
        ):
            res = client.get(f"/api/v1/geoportal/stations/{station_id}/animals")

        assert res.status_code == 200


class TestListStationActivity:
    def test_requires_authentication(self):
        client = _make_no_auth_client()
        res = client.get(f"/api/v1/geoportal/stations/{uuid.uuid4()}/activity")
        assert res.status_code == 401

    def test_returns_empty_list_when_no_activity(self):
        client = _make_auth_client(UserRole.researcher)
        station_id = uuid.uuid4()
        with patch(
            "modules.geoportal.router.GeoportalService.list_station_activity",
            new=AsyncMock(return_value=[]),
        ):
            res = client.get(f"/api/v1/geoportal/stations/{station_id}/activity")

        assert res.status_code == 200
        assert res.json() == []

    def test_returns_mixed_activity_feed(self):
        client = _make_auth_client(UserRole.researcher)
        station_id = uuid.uuid4()
        feed = [
            _make_activity_item(
                item_type=ActivityItemType.rfid_read,
                description="RFID leído: RFID-001 · 95 g",
                rfid_tag="RFID-001",
            ),
            _make_activity_item(
                item_type=ActivityItemType.alert,
                description="Alerta: empty_tank",
                severity="critical",
            ),
            _make_activity_item(
                item_type=ActivityItemType.telemetry,
                description="Telemetría recibida · 28.5 °C · 72% HR",
                severity="info",
            ),
        ]
        with patch(
            "modules.geoportal.router.GeoportalService.list_station_activity",
            new=AsyncMock(return_value=feed),
        ):
            res = client.get(f"/api/v1/geoportal/stations/{station_id}/activity")

        assert res.status_code == 200
        data = res.json()
        assert len(data) == 3
        assert data[0]["item_type"] == "rfid_read"
        assert data[0]["rfid_tag"] == "RFID-001"
        assert data[1]["item_type"] == "alert"
        assert data[1]["severity"] == "critical"
        assert data[2]["item_type"] == "telemetry"

    def test_limit_param_accepted(self):
        client = _make_auth_client(UserRole.researcher)
        station_id = uuid.uuid4()
        with patch(
            "modules.geoportal.router.GeoportalService.list_station_activity",
            new=AsyncMock(return_value=[]),
        ):
            res = client.get(
                f"/api/v1/geoportal/stations/{station_id}/activity?limit=5"
            )

        assert res.status_code == 200

    def test_limit_param_rejects_zero(self):
        client = _make_auth_client(UserRole.researcher)
        station_id = uuid.uuid4()
        res = client.get(
            f"/api/v1/geoportal/stations/{station_id}/activity?limit=0"
        )
        assert res.status_code == 422

    def test_limit_param_rejects_above_50(self):
        client = _make_auth_client(UserRole.researcher)
        station_id = uuid.uuid4()
        res = client.get(
            f"/api/v1/geoportal/stations/{station_id}/activity?limit=51"
        )
        assert res.status_code == 422

    def test_all_activity_item_types_serialize_correctly(self):
        client = _make_auth_client(UserRole.admin)
        station_id = uuid.uuid4()
        ts = datetime.now(timezone.utc)
        feed = [
            _make_activity_item(ActivityItemType.feeding, "Alimentación", timestamp=ts),
            _make_activity_item(ActivityItemType.rfid_read, "RFID leído", timestamp=ts),
            _make_activity_item(
                ActivityItemType.photo, "Foto capturada", timestamp=ts,
                media_urls=["https://cdn.example.com/photo.jpg"],
            ),
            _make_activity_item(ActivityItemType.alert, "Alerta", timestamp=ts, severity="warning"),
            _make_activity_item(ActivityItemType.telemetry, "Telemetría", timestamp=ts, severity="info"),
        ]
        with patch(
            "modules.geoportal.router.GeoportalService.list_station_activity",
            new=AsyncMock(return_value=feed),
        ):
            res = client.get(f"/api/v1/geoportal/stations/{station_id}/activity")

        assert res.status_code == 200
        types_in_response = {item["item_type"] for item in res.json()}
        assert types_in_response == {"feeding", "rfid_read", "photo", "alert", "telemetry"}


def _make_stats_response(**kwargs) -> GeoportalStatsResponse:
    return GeoportalStatsResponse(
        time_filter=kwargs.get("time_filter", "7d"),
        total_estaciones=kwargs.get("total_estaciones", 2),
        total_sectores=kwargs.get("total_sectores", 1),
        total_animales_con_chip=kwargs.get("total_animales_con_chip", 3),
        total_visitas=kwargs.get("total_visitas", 50),
        avistamientos_sin_chip=kwargs.get("avistamientos_sin_chip", 15),
        estaciones=kwargs.get("estaciones", []),
        sectores=kwargs.get("sectores", []),
        animales_con_chip=kwargs.get("animales_con_chip", []),
    )


class TestGetGeoportalStats:
    def test_requires_authentication(self):
        client = _make_no_auth_client()
        res = client.get("/api/v1/geoportal/stats")
        assert res.status_code == 401

    def test_returns_stats_response_with_correct_schema(self):
        client = _make_auth_client(UserRole.researcher)
        stats = _make_stats_response(
            total_estaciones=4,
            total_sectores=2,
            total_animales_con_chip=8,
            total_visitas=120,
            avistamientos_sin_chip=40,
        )
        with patch(
            "modules.geoportal.router.GeoportalService.get_global_stats",
            new=AsyncMock(return_value=stats),
        ):
            res = client.get("/api/v1/geoportal/stats")

        assert res.status_code == 200
        data = res.json()
        assert data["total_estaciones"] == 4
        assert data["total_sectores"] == 2
        assert data["total_animales_con_chip"] == 8
        assert data["total_visitas"] == 120
        assert data["avistamientos_sin_chip"] == 40
        assert "estaciones" in data
        assert "sectores" in data
        assert "animales_con_chip" in data
        assert isinstance(data["estaciones"], list)

    def test_accepts_time_filter_query_param(self):
        client = _make_auth_client(UserRole.admin)
        stats = _make_stats_response(time_filter="30d")
        with patch(
            "modules.geoportal.router.GeoportalService.get_global_stats",
            new=AsyncMock(return_value=stats),
        ) as mock:
            res = client.get("/api/v1/geoportal/stats?time_filter=30d")

        assert res.status_code == 200

    def test_field_operator_can_access(self):
        client = _make_auth_client(UserRole.field_operator)
        stats = _make_stats_response()
        with patch(
            "modules.geoportal.router.GeoportalService.get_global_stats",
            new=AsyncMock(return_value=stats),
        ):
            res = client.get("/api/v1/geoportal/stats")

        assert res.status_code == 200


def _make_history_response(**kwargs) -> AnimalHistoryResponse:
    ts = datetime(2026, 7, 8, 10, 0, 0, tzinfo=timezone.utc)
    sid = str(uuid.uuid4())
    return AnimalHistoryResponse(
        animal_id=kwargs.get("animal_id", str(uuid.uuid4())),
        rfid_tag=kwargs.get("rfid_tag", "RFID-TEST-001"),
        species=kwargs.get("species", "Oso hormiguero"),
        sex=kwargs.get("sex", "male"),
        estimated_age=kwargs.get("estimated_age", "adult"),
        notes=None,
        total_alimentaciones=kwargs.get("total_alimentaciones", 11),
        total_estaciones=kwargs.get("total_estaciones", 2),
        dias_activo=kwargs.get("dias_activo", 7),
        peso_promedio_g=kwargs.get("peso_promedio_g", 198.5),
        actividad_semanal=kwargs.get("actividad_semanal", [1, 2, 1, 2, 2, 1, 2]),
        feeder_ranking=[
            FeederRankItem(station_id=sid, station_name="Comedero Norte", visits=7, pct=63.6, is_primary=True),
        ],
        timeline=[
            FeedingEvent(event_id=str(uuid.uuid4()), station_id=sid, station_name="Comedero Norte", timestamp=ts, consumed_g=210.0),
        ],
        trace_path=[
            TraceStop(station_id=sid, station_name="Comedero Norte", lat=4.71, lng=-74.07, timestamp=ts),
        ],
        insight_text=kwargs.get("insight_text", "Uso distribuido entre 2 comederos"),
        time_filter=kwargs.get("time_filter", "all"),
    )


class TestGetAnimalHistory:
    def test_requires_authentication(self):
        client = _make_no_auth_client()
        res = client.get(f"/api/v1/geoportal/animals/{uuid.uuid4()}/history")
        assert res.status_code == 401

    def test_returns_404_when_animal_not_found(self):
        client = _make_auth_client(UserRole.researcher)
        with patch(
            "modules.geoportal.router.GeoportalService.get_animal_history",
            new=AsyncMock(return_value=None),
        ):
            res = client.get(f"/api/v1/geoportal/animals/{uuid.uuid4()}/history")

        assert res.status_code == 404

    def test_returns_history_with_correct_schema(self):
        client = _make_auth_client(UserRole.researcher)
        animal_id = str(uuid.uuid4())
        history = _make_history_response(animal_id=animal_id, total_alimentaciones=11, dias_activo=7)
        with patch(
            "modules.geoportal.router.GeoportalService.get_animal_history",
            new=AsyncMock(return_value=history),
        ):
            res = client.get(f"/api/v1/geoportal/animals/{animal_id}/history")

        assert res.status_code == 200
        data = res.json()
        assert data["animal_id"] == animal_id
        assert data["rfid_tag"] == "RFID-TEST-001"
        assert data["species"] == "Oso hormiguero"
        assert data["total_alimentaciones"] == 11
        assert data["dias_activo"] == 7
        assert len(data["actividad_semanal"]) == 7
        assert "feeder_ranking" in data
        assert "timeline" in data
        assert "trace_path" in data
        assert "insight_text" in data
        # Trace stop has lat/lng
        assert data["trace_path"][0]["lat"] == 4.71

    def test_accepts_time_filter_all(self):
        client = _make_auth_client(UserRole.admin)
        history = _make_history_response(time_filter="all")
        with patch(
            "modules.geoportal.router.GeoportalService.get_animal_history",
            new=AsyncMock(return_value=history),
        ):
            res = client.get(
                f"/api/v1/geoportal/animals/{uuid.uuid4()}/history?time_filter=all"
            )

        assert res.status_code == 200
        assert res.json()["time_filter"] == "all"


def _make_events_response(
    station_id: str | None = None,
    page: int = 1,
    total: int = 2,
    **kwargs,
) -> StationEventsResponse:
    sid = station_id or str(uuid.uuid4())
    ts = datetime(2026, 7, 9, 10, 0, 0, tzinfo=timezone.utc)
    return StationEventsResponse(
        station_id=sid,
        station_name=kwargs.get("station_name", "Comedero Norte"),
        total=total,
        identificadas=kwargs.get("identificadas", 1),
        sin_identificar=kwargs.get("sin_identificar", 1),
        page=page,
        pages=kwargs.get("pages", 1),
        events=[
            StationEventDetail(
                event_id=str(uuid.uuid4()),
                timestamp=ts,
                rfid_tag="RFID-001",
                animal_id=str(uuid.uuid4()),
                animal_species="Oso hormiguero",
                animal_sex="male",
                consumed_g=210.0,
                temperature_c=25.0,
                humidity_pct=68.0,
                media_urls=[],
                is_identified=True,
            ),
            StationEventDetail(
                event_id=str(uuid.uuid4()),
                timestamp=ts,
                rfid_tag=None,
                consumed_g=45.0,
                temperature_c=42.0,
                humidity_pct=18.0,
                is_identified=False,
            ),
        ],
    )


class TestGetStationEvents:
    def test_requires_authentication(self):
        client = _make_no_auth_client()
        res = client.get(f"/api/v1/geoportal/stations/{uuid.uuid4()}/events")
        assert res.status_code == 401

    def test_returns_404_when_station_not_found(self):
        client = _make_auth_client(UserRole.researcher)
        with patch(
            "modules.geoportal.router.GeoportalService.get_station_events",
            new=AsyncMock(return_value=None),
        ):
            res = client.get(f"/api/v1/geoportal/stations/{uuid.uuid4()}/events")
        assert res.status_code == 404

    def test_returns_events_with_correct_schema(self):
        client = _make_auth_client(UserRole.researcher)
        sid = str(uuid.uuid4())
        response = _make_events_response(station_id=sid, total=2, identificadas=1, sin_identificar=1)
        with patch(
            "modules.geoportal.router.GeoportalService.get_station_events",
            new=AsyncMock(return_value=response),
        ):
            res = client.get(f"/api/v1/geoportal/stations/{sid}/events")

        assert res.status_code == 200
        data = res.json()
        assert data["station_id"] == sid
        assert data["total"] == 2
        assert data["identificadas"] == 1
        assert data["sin_identificar"] == 1
        assert data["page"] == 1
        assert "pages" in data
        assert isinstance(data["events"], list)
        assert len(data["events"]) == 2
        ev = data["events"][0]
        assert ev["is_identified"] is True
        assert ev["animal_species"] == "Oso hormiguero"
        assert ev["consumed_g"] == 210.0

    def test_filter_param_accepted(self):
        client = _make_auth_client(UserRole.admin)
        response = _make_events_response(total=1, identificadas=1, sin_identificar=0)
        with patch(
            "modules.geoportal.router.GeoportalService.get_station_events",
            new=AsyncMock(return_value=response),
        ):
            res = client.get(
                f"/api/v1/geoportal/stations/{uuid.uuid4()}/events?filter=identified"
            )
        assert res.status_code == 200

    def test_invalid_filter_rejected(self):
        client = _make_auth_client(UserRole.researcher)
        res = client.get(
            f"/api/v1/geoportal/stations/{uuid.uuid4()}/events?filter=invalid"
        )
        assert res.status_code == 422
