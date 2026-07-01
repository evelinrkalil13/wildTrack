import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.iot_events.service import IotEventService
from shared.enums import AlertType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_device(station_id=None):
    d = MagicMock()
    d.id = uuid.uuid4()
    d.station_id = station_id or uuid.uuid4()
    return d


def _make_animal():
    a = MagicMock()
    a.id = uuid.uuid4()
    return a


def _make_session_ctx():
    """Returns (factory, session) where factory() is an async context manager."""
    session = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=ctx)
    return factory, session


def _feeding_payload(**overrides) -> bytes:
    base = {
        "event_id": str(uuid.uuid4()),
        "event_type": "feeding_session",
        "device_id": str(uuid.uuid4()),
        "timestamp": "2024-01-01T12:00:00Z",
        "rfid": {"detected": False, "tag": None, "read_quality": None},
        "sensors": {
            "temperature_c": 22.5, "humidity_pct": 68.0,
            "initial_weight_g": 500.0, "final_weight_g": 420.0, "consumed_g": 80.0,
        },
        "media": {"captured": 0, "urls": []},
        "device_status": {"wifi_rssi_dbm": -62, "firmware_version": "1.2.0", "battery_pct": None},
    }
    base.update(overrides)
    return json.dumps(base).encode()


# ---------------------------------------------------------------------------
# process_feeding_event
# ---------------------------------------------------------------------------

class TestProcessFeedingEvent:
    async def test_enriches_station_fields_and_stores_event(self):
        device_id = str(uuid.uuid4())
        station_id = uuid.uuid4()
        zone_id = uuid.uuid4()
        device = _make_device(station_id=station_id)
        raw = _feeding_payload(device_id=device_id)
        mock_session_factory, _ = _make_session_ctx()
        inserted_doc = {}

        async def _capture_insert(doc):
            inserted_doc.update(doc)
            return True

        with (
            patch("modules.iot_events.service.AsyncSessionLocal", new=mock_session_factory),
            patch(
                "modules.iot_events.service.DeviceRepository.find_by_id_with_station",
                new=AsyncMock(return_value=(device, "STN-001", zone_id)),
            ),
            patch(
                "modules.iot_events.service.AnimalRepository.find_by_rfid",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.iot_events.service.IotEventRepository.insert_event",
                new=AsyncMock(side_effect=_capture_insert),
            ),
            patch(
                "modules.iot_events.service.DeviceRepository.update_last_seen",
                new=AsyncMock(),
            ),
        ):
            await IotEventService.process_feeding_event(device_id, raw)

        assert inserted_doc["device_id"] == device_id
        assert inserted_doc["station_id"] == str(station_id)
        assert inserted_doc["station_code"] == "STN-001"
        assert inserted_doc["zone_id"] == str(zone_id)

    async def test_resolves_animal_by_rfid(self):
        device_id = str(uuid.uuid4())
        station_id = uuid.uuid4()
        animal = _make_animal()
        raw = _feeding_payload(
            device_id=device_id,
            rfid={"detected": True, "tag": "RFID-001", "read_quality": "good"},
        )
        mock_session_factory, _ = _make_session_ctx()
        inserted_doc = {}

        async def _capture_insert(doc):
            inserted_doc.update(doc)
            return True

        with (
            patch("modules.iot_events.service.AsyncSessionLocal", new=mock_session_factory),
            patch(
                "modules.iot_events.service.DeviceRepository.find_by_id_with_station",
                new=AsyncMock(return_value=(_make_device(station_id=station_id), "STN-001", uuid.uuid4())),
            ),
            patch(
                "modules.iot_events.service.AnimalRepository.find_by_rfid",
                new=AsyncMock(return_value=animal),
            ),
            patch(
                "modules.iot_events.service.IotEventRepository.insert_event",
                new=AsyncMock(side_effect=_capture_insert),
            ),
            patch(
                "modules.iot_events.service.DeviceRepository.update_last_seen",
                new=AsyncMock(),
            ),
        ):
            await IotEventService.process_feeding_event(device_id, raw)

        assert inserted_doc["animal_id"] == str(animal.id)
        assert inserted_doc["rfid_tag"] == "RFID-001"

    async def test_no_animal_match_stores_null_animal_id(self):
        device_id = str(uuid.uuid4())
        raw = _feeding_payload(
            device_id=device_id,
            rfid={"detected": True, "tag": "RFID-UNKNOWN", "read_quality": "good"},
        )
        mock_session_factory, _ = _make_session_ctx()
        inserted_doc = {}

        async def _capture_insert(doc):
            inserted_doc.update(doc)
            return True

        with (
            patch("modules.iot_events.service.AsyncSessionLocal", new=mock_session_factory),
            patch(
                "modules.iot_events.service.DeviceRepository.find_by_id_with_station",
                new=AsyncMock(return_value=(_make_device(), "STN-001", uuid.uuid4())),
            ),
            patch(
                "modules.iot_events.service.AnimalRepository.find_by_rfid",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.iot_events.service.IotEventRepository.insert_event",
                new=AsyncMock(side_effect=_capture_insert),
            ),
            patch(
                "modules.iot_events.service.DeviceRepository.update_last_seen",
                new=AsyncMock(),
            ),
            patch(
                "modules.iot_events.service.AlertService.raise_alert",
                new=AsyncMock(),
            ),
        ):
            await IotEventService.process_feeding_event(device_id, raw)

        assert inserted_doc["animal_id"] is None

    async def test_dead_letters_unknown_device(self):
        device_id = str(uuid.uuid4())
        raw = _feeding_payload(device_id=device_id)
        mock_session_factory, _ = _make_session_ctx()
        mock_dead_letter = AsyncMock()

        with (
            patch("modules.iot_events.service.AsyncSessionLocal", new=mock_session_factory),
            patch(
                "modules.iot_events.service.DeviceRepository.find_by_id_with_station",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.iot_events.service.IotEventRepository.insert_dead_letter",
                new=mock_dead_letter,
            ),
            patch(
                "modules.iot_events.service.IotEventRepository.insert_event",
                new=AsyncMock(),
            ),
        ):
            await IotEventService.process_feeding_event(device_id, raw)

        mock_dead_letter.assert_awaited_once()
        call_args = mock_dead_letter.call_args[0][0]
        assert call_args["reason"] == "unknown_device"

    async def test_dead_letters_invalid_json(self):
        device_id = str(uuid.uuid4())
        mock_dead_letter = AsyncMock()

        with patch(
            "modules.iot_events.service.IotEventRepository.insert_dead_letter",
            new=mock_dead_letter,
        ):
            await IotEventService.process_feeding_event(device_id, b"not valid json {{{")

        mock_dead_letter.assert_awaited_once()
        assert mock_dead_letter.call_args[0][0]["reason"] == "json_decode_error"

    async def test_ignores_duplicate_event_id(self):
        device_id = str(uuid.uuid4())
        raw = _feeding_payload(device_id=device_id)
        mock_session_factory, _ = _make_session_ctx()
        mock_update_last_seen = AsyncMock()

        with (
            patch("modules.iot_events.service.AsyncSessionLocal", new=mock_session_factory),
            patch(
                "modules.iot_events.service.DeviceRepository.find_by_id_with_station",
                new=AsyncMock(return_value=(_make_device(), "STN-001", uuid.uuid4())),
            ),
            patch(
                "modules.iot_events.service.AnimalRepository.find_by_rfid",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.iot_events.service.IotEventRepository.insert_event",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "modules.iot_events.service.DeviceRepository.update_last_seen",
                new=mock_update_last_seen,
            ),
        ):
            await IotEventService.process_feeding_event(device_id, raw)

        mock_update_last_seen.assert_not_awaited()

    async def test_raises_rfid_alert_on_hardware_failure(self):
        device_id = str(uuid.uuid4())
        station_id = uuid.uuid4()
        raw = _feeding_payload(
            device_id=device_id,
            rfid={"detected": True, "tag": None, "read_quality": "retry"},
        )
        mock_session_factory, _ = _make_session_ctx()
        mock_raise_alert = AsyncMock()

        with (
            patch("modules.iot_events.service.AsyncSessionLocal", new=mock_session_factory),
            patch(
                "modules.iot_events.service.DeviceRepository.find_by_id_with_station",
                new=AsyncMock(return_value=(_make_device(station_id=station_id), "STN-001", uuid.uuid4())),
            ),
            patch(
                "modules.iot_events.service.IotEventRepository.insert_event",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "modules.iot_events.service.DeviceRepository.update_last_seen",
                new=AsyncMock(),
            ),
            patch(
                "modules.iot_events.service.AlertService.raise_alert",
                new=mock_raise_alert,
            ),
        ):
            await IotEventService.process_feeding_event(device_id, raw)

        mock_raise_alert.assert_awaited_once()
        assert mock_raise_alert.call_args.kwargs["alert_type"] == AlertType.rfid_read_failure

    async def test_process_telemetry_stores_document_and_updates_last_seen(self):
        device_id = str(uuid.uuid4())
        device = _make_device()
        raw = json.dumps({
            "device_id": device_id,
            "timestamp": "2024-01-01T12:00:00Z",
            "sensors": {"temperature_c": 22.5, "humidity_pct": 68.0},
            "device_status": {"wifi_rssi_dbm": -62, "firmware_version": "1.2.0", "battery_pct": 85.0},
        }).encode()
        mock_session_factory, _ = _make_session_ctx()
        mock_insert_telemetry = AsyncMock()
        mock_update_last_seen = AsyncMock()

        with (
            patch("modules.iot_events.service.AsyncSessionLocal", new=mock_session_factory),
            patch(
                "modules.iot_events.service.DeviceRepository.find_by_id",
                new=AsyncMock(return_value=device),
            ),
            patch(
                "modules.iot_events.service.IotEventRepository.insert_telemetry",
                new=mock_insert_telemetry,
            ),
            patch(
                "modules.iot_events.service.DeviceRepository.update_last_seen",
                new=mock_update_last_seen,
            ),
        ):
            await IotEventService.process_telemetry(device_id, raw)

        mock_insert_telemetry.assert_awaited_once()
        doc = mock_insert_telemetry.call_args[0][0]
        assert doc["device_id"] == device_id
        assert doc["temperature_c"] == 22.5
        mock_update_last_seen.assert_awaited_once()
