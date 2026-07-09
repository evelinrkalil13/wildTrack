import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.geoportal.aggregation import StationCounts, StationDetailStats
from modules.geoportal.schemas import GeoportalStationDetail, GeoportalStationMapItem
from modules.geoportal.service import GeoportalService
from shared.enums import DeviceStatus, StationStatus, TimeFilter


def _make_station_row(
    station_id=None,
    code="STA-001",
    name="Comedero Norte",
    status=StationStatus.active,
    lat=4.71,
    lon=-74.07,
    zone_id=None,
    zone_name="Zona Norte",
    zone_color="#52b788",
):
    row = MagicMock()
    row.station_id = station_id or uuid.uuid4()
    row.station_code = code
    row.station_name = name
    row.station_status = status
    row.latitude = lat
    row.longitude = lon
    row.zone_id = zone_id or uuid.uuid4()
    row.zone_name = zone_name
    row.zone_color = zone_color
    return row


def _make_device(station_id=None, status=DeviceStatus.online):
    d = MagicMock()
    d.id = uuid.uuid4()
    d.serial_number = "WT-ESP32-0001"
    d.status = status
    d.last_seen = datetime.now(timezone.utc)
    d.station_id = station_id or uuid.uuid4()
    return d


def _make_telemetry_doc(station_id: str) -> dict:
    return {
        "station_id": station_id,
        "temperature_c": 27.5,
        "humidity_pct": 65.0,
        "wifi_rssi_dbm": -72,
        "firmware_version": "1.2.0",
        "ingested_at": datetime.now(timezone.utc),
    }


def _make_event_doc(station_id: str, event_id: str | None = None) -> dict:
    return {
        "event_id": event_id or str(uuid.uuid4()),
        "station_id": station_id,
        "rfid_tag": "AABB1122",
        "consumed_g": 85.0,
        "photos_count": 1,
        "ingested_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def session():
    return AsyncMock()


class TestListStations:
    async def test_returns_empty_list_when_no_stations(self, session):
        with patch(
            "modules.geoportal.service.GeoportalRepository.list_all_stations_with_zones",
            new=AsyncMock(return_value=[]),
        ):
            result = await GeoportalService.list_stations(session)

        assert result == []

    async def test_returns_station_with_no_mongo_data(self, session):
        row = _make_station_row()
        station_id_str = str(row.station_id)

        with (
            patch(
                "modules.geoportal.service.GeoportalRepository.list_all_stations_with_zones",
                new=AsyncMock(return_value=[row]),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.list_assigned_devices_by_station",
                new=AsyncMock(return_value={}),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_open_alert_counts_by_station",
                new=AsyncMock(return_value={}),
            ),
            patch(
                "modules.geoportal.service.GeoportalAggregationService.compute_station_counts",
                new=AsyncMock(return_value={}),
            ),
        ):
            result = await GeoportalService.list_stations(session)

        assert len(result) == 1
        item = result[0]
        assert item.station_id == station_id_str
        assert item.station_code == "STA-001"
        assert item.zone_color == "#52b788"
        assert item.is_live is False
        assert item.device_status is None
        assert item.open_alerts_count == 0
        assert item.visitas_total == 0
        assert item.visitas_sin_identificar == 0

    async def test_merges_device_counts_and_alerts(self, session):
        row = _make_station_row()
        station_id_str = str(row.station_id)
        device = _make_device(station_id=row.station_id, status=DeviceStatus.online)
        counts = StationCounts(visitas_total=47, visitas_identificadas=32, visitas_sin_identificar=15)

        with (
            patch(
                "modules.geoportal.service.GeoportalRepository.list_all_stations_with_zones",
                new=AsyncMock(return_value=[row]),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.list_assigned_devices_by_station",
                new=AsyncMock(return_value={station_id_str: device}),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_open_alert_counts_by_station",
                new=AsyncMock(return_value={station_id_str: 2}),
            ),
            patch(
                "modules.geoportal.service.GeoportalAggregationService.compute_station_counts",
                new=AsyncMock(return_value={station_id_str: counts}),
            ),
        ):
            result = await GeoportalService.list_stations(session)

        assert len(result) == 1
        item = result[0]
        assert item.is_live is True
        assert item.device_status == DeviceStatus.online
        assert item.open_alerts_count == 2
        assert item.visitas_total == 47
        assert item.visitas_identificadas == 32
        assert item.visitas_sin_identificar == 15

    async def test_station_returns_validated_schema(self, session):
        row = _make_station_row(status=StationStatus.maintenance)

        with (
            patch(
                "modules.geoportal.service.GeoportalRepository.list_all_stations_with_zones",
                new=AsyncMock(return_value=[row]),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.list_assigned_devices_by_station",
                new=AsyncMock(return_value={}),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_open_alert_counts_by_station",
                new=AsyncMock(return_value={}),
            ),
            patch(
                "modules.geoportal.service.GeoportalAggregationService.compute_station_counts",
                new=AsyncMock(return_value={}),
            ),
        ):
            result = await GeoportalService.list_stations(session)

        assert isinstance(result[0], GeoportalStationMapItem)
        assert result[0].status == StationStatus.maintenance
        assert result[0].latitude == pytest.approx(4.71)
        assert result[0].longitude == pytest.approx(-74.07)


class TestGetStationDetail:
    async def test_returns_none_when_station_not_found(self, session):
        with patch(
            "modules.geoportal.service.GeoportalRepository.get_station_with_zone_by_id",
            new=AsyncMock(return_value=None),
        ):
            result = await GeoportalService.get_station_detail(session, str(uuid.uuid4()))

        assert result is None

    async def test_returns_detail_with_device_and_telemetry(self, session):
        row = _make_station_row()
        station_id_str = str(row.station_id)
        device = _make_device(station_id=row.station_id, status=DeviceStatus.online)
        telemetry = _make_telemetry_doc(station_id_str)
        event = _make_event_doc(station_id_str)
        stats = StationDetailStats(
            visitas_total=10,
            visitas_identificadas=7,
            visitas_sin_identificar=3,
            peso_promedio_g=210.0,
            peso_mediana_g=200.0,
            visitas_por_dia=[2, 1, 3, 2, 1, 1, 0],
        )

        with (
            patch(
                "modules.geoportal.service.GeoportalRepository.get_station_with_zone_by_id",
                new=AsyncMock(return_value=row),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_device_for_station",
                new=AsyncMock(return_value=device),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_latest_telemetry_for_station",
                new=AsyncMock(return_value=telemetry),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_recent_events_for_station",
                new=AsyncMock(return_value=[event]),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_open_alert_count_for_station",
                new=AsyncMock(return_value=1),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_active_food_for_station",
                new=AsyncMock(return_value="Maíz"),
            ),
            patch(
                "modules.geoportal.service.GeoportalAggregationService.compute_station_detail_stats",
                new=AsyncMock(return_value=stats),
            ),
        ):
            result = await GeoportalService.get_station_detail(session, station_id_str)

        assert isinstance(result, GeoportalStationDetail)
        assert result.station_id == station_id_str
        assert result.is_live is True
        assert result.device is not None
        assert result.device.serial_number == "WT-ESP32-0001"
        assert result.latest_telemetry is not None
        assert result.latest_telemetry.temperature_c == 27.5
        assert result.visitas_total == 10
        assert result.peso_promedio_g == 210.0
        assert result.peso_mediana_g == 200.0
        assert result.visitas_por_dia == [2, 1, 3, 2, 1, 1, 0]
        assert result.food_type == "Maíz"
        assert result.open_alerts_count == 1
        assert len(result.recent_events) == 1
        assert result.recent_events[0].rfid_tag == "AABB1122"

    async def test_returns_detail_with_no_device(self, session):
        row = _make_station_row()
        station_id_str = str(row.station_id)
        stats = StationDetailStats()

        with (
            patch(
                "modules.geoportal.service.GeoportalRepository.get_station_with_zone_by_id",
                new=AsyncMock(return_value=row),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_device_for_station",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_latest_telemetry_for_station",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_recent_events_for_station",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_open_alert_count_for_station",
                new=AsyncMock(return_value=0),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_active_food_for_station",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.geoportal.service.GeoportalAggregationService.compute_station_detail_stats",
                new=AsyncMock(return_value=stats),
            ),
        ):
            result = await GeoportalService.get_station_detail(session, station_id_str)

        assert result is not None
        assert result.device is None
        assert result.is_live is False
        assert result.device_status is None
        assert result.latest_telemetry is None
        assert result.recent_events == []
        assert result.food_type is None

    async def test_is_live_false_when_device_offline(self, session):
        row = _make_station_row()
        station_id_str = str(row.station_id)
        device = _make_device(station_id=row.station_id, status=DeviceStatus.offline)
        stats = StationDetailStats()

        with (
            patch(
                "modules.geoportal.service.GeoportalRepository.get_station_with_zone_by_id",
                new=AsyncMock(return_value=row),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_device_for_station",
                new=AsyncMock(return_value=device),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_latest_telemetry_for_station",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_recent_events_for_station",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_open_alert_count_for_station",
                new=AsyncMock(return_value=0),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_active_food_for_station",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.geoportal.service.GeoportalAggregationService.compute_station_detail_stats",
                new=AsyncMock(return_value=stats),
            ),
        ):
            result = await GeoportalService.get_station_detail(session, station_id_str)

        assert result is not None
        assert result.is_live is False
        assert result.device_status == DeviceStatus.offline
