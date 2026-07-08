import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.geoportal.schemas import GeoportalStationRead
from modules.geoportal.service import GeoportalService
from shared.enums import DeviceStatus, StationStatus


def _make_station_row(
    station_id=None,
    code="STA-001",
    name="Comedero Norte",
    status=StationStatus.active,
    lat=4.71,
    lon=-74.07,
    zone_id=None,
    zone_name="Zona Norte",
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
    return row


def _make_device(station_id=None):
    d = MagicMock()
    d.id = uuid.uuid4()
    d.serial_number = "WT-ESP32-0001"
    d.status = DeviceStatus.online
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
        with (
            patch(
                "modules.geoportal.service.GeoportalRepository.list_all_stations_with_zones",
                new=AsyncMock(return_value=[]),
            ),
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
                "modules.geoportal.service.GeoportalRepository.get_latest_telemetry_by_station",
                new=AsyncMock(return_value={}),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_recent_events_by_station",
                new=AsyncMock(return_value={}),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_open_alert_counts_by_station",
                new=AsyncMock(return_value={}),
            ),
        ):
            result = await GeoportalService.list_stations(session)

        assert len(result) == 1
        item = result[0]
        assert item.station_id == station_id_str
        assert item.station_code == "STA-001"
        assert item.device is None
        assert item.latest_telemetry is None
        assert item.recent_events == []
        assert item.open_alerts_count == 0

    async def test_merges_device_telemetry_events_and_alerts(self, session):
        row = _make_station_row()
        station_id_str = str(row.station_id)
        device = _make_device(station_id=row.station_id)
        telemetry = _make_telemetry_doc(station_id_str)
        event = _make_event_doc(station_id_str)

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
                "modules.geoportal.service.GeoportalRepository.get_latest_telemetry_by_station",
                new=AsyncMock(return_value={station_id_str: telemetry}),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_recent_events_by_station",
                new=AsyncMock(return_value={station_id_str: [event]}),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_open_alert_counts_by_station",
                new=AsyncMock(return_value={station_id_str: 2}),
            ),
        ):
            result = await GeoportalService.list_stations(session)

        assert len(result) == 1
        item = result[0]
        assert item.device is not None
        assert item.device.serial_number == "WT-ESP32-0001"
        assert item.latest_telemetry is not None
        assert item.latest_telemetry.temperature_c == 27.5
        assert len(item.recent_events) == 1
        assert item.recent_events[0].rfid_tag == "AABB1122"
        assert item.open_alerts_count == 2

    async def test_station_returns_validated_schema(self, session):
        row = _make_station_row(status=StationStatus.maintenance)
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
                "modules.geoportal.service.GeoportalRepository.get_latest_telemetry_by_station",
                new=AsyncMock(return_value={}),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_recent_events_by_station",
                new=AsyncMock(return_value={}),
            ),
            patch(
                "modules.geoportal.service.GeoportalRepository.get_open_alert_counts_by_station",
                new=AsyncMock(return_value={}),
            ),
        ):
            result = await GeoportalService.list_stations(session)

        assert isinstance(result[0], GeoportalStationRead)
        assert result[0].status == StationStatus.maintenance
        assert result[0].latitude == pytest.approx(4.71)
        assert result[0].longitude == pytest.approx(-74.07)
