import json
import logging

# strict=False allows unescaped control characters in JSON strings.
# ESP32 firmware may embed raw RFID bytes directly in string fields.
_decoder = json.JSONDecoder(strict=False)
from datetime import datetime, timezone
from uuid import UUID

from infrastructure.postgres import AsyncSessionLocal
from modules.alerts.service import AlertService
from modules.animals.repository import AnimalRepository
from modules.devices.repository import DeviceRepository
from modules.iot_events.repository import IotEventRepository
from modules.iot_events.schemas import FeedingEventPayload, StatusPayload, TelemetryPayload
from shared.enums import AlertType

logger = logging.getLogger(__name__)


class IotEventService:
    @staticmethod
    async def process_feeding_event(device_id: str, raw: bytes) -> None:
        try:
            data = _decoder.decode(raw.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error("MQTT JSON decode error on events topic device=%s: %s", device_id, exc)
            await IotEventRepository.insert_dead_letter({
                "topic": f"wildtrack/devices/{device_id}/events",
                "raw_payload": raw.decode("utf-8", errors="replace"),
                "reason": "json_decode_error",
                "error_detail": str(exc),
                "received_at": datetime.now(timezone.utc),
            })
            return

        try:
            payload = FeedingEventPayload.model_validate(data)
        except Exception as exc:
            logger.warning("MQTT payload validation error device=%s: %s", device_id, exc)
            await IotEventRepository.insert_dead_letter({
                "topic": f"wildtrack/devices/{device_id}/events",
                "raw_payload": data,
                "reason": "validation_error",
                "error_detail": str(exc),
                "received_at": datetime.now(timezone.utc),
            })
            return

        async with AsyncSessionLocal() as session:
            row = await DeviceRepository.find_by_id_with_station(session, UUID(device_id))

        if row is None:
            logger.warning("MQTT event from unknown device_id=%s", device_id)
            await IotEventRepository.insert_dead_letter({
                "topic": f"wildtrack/devices/{device_id}/events",
                "raw_payload": data,
                "reason": "unknown_device",
                "error_detail": f"device_id={device_id} not found",
                "received_at": datetime.now(timezone.utc),
            })
            return

        device, station_code, zone_id = row

        if device.station_id is None:
            logger.warning("MQTT event from unassigned device_id=%s", device_id)
            await IotEventRepository.insert_dead_letter({
                "topic": f"wildtrack/devices/{device_id}/events",
                "raw_payload": data,
                "reason": "device_unassigned",
                "error_detail": f"device_id={device_id} has no station",
                "received_at": datetime.now(timezone.utc),
            })
            return

        station_id = str(device.station_id)

        animal_id = None
        if payload.rfid.detected and payload.rfid.tag:
            async with AsyncSessionLocal() as session:
                animal = await AnimalRepository.find_by_rfid(session, payload.rfid.tag)
            if animal is not None:
                animal_id = str(animal.id)
            else:
                logger.info("RFID tag %s not matched to any animal", payload.rfid.tag)

        if payload.rfid.detected and not payload.rfid.tag and payload.rfid.read_quality == "retry":
            await AlertService.raise_alert(
                alert_type=AlertType.rfid_read_failure,
                station_id=station_id,
                device_id=device_id,
                event_id=payload.event_id,
                message=f"RFID hardware read failure at station {station_code or station_id}",
            )

        doc = {
            "event_id": payload.event_id,
            "event_type": payload.event_type,
            "device_id": device_id,
            "station_id": station_id,
            "station_code": station_code,
            "zone_id": str(zone_id) if zone_id else None,
            "animal_id": animal_id,
            "rfid_tag": payload.rfid.tag,
            "rfid_detected": payload.rfid.detected,
            "rfid_read_quality": payload.rfid.read_quality,
            "temperature_c": payload.sensors.temperature_c,
            "humidity_pct": payload.sensors.humidity_pct,
            "initial_weight_g": payload.sensors.initial_weight_g,
            "final_weight_g": payload.sensors.final_weight_g,
            "consumed_g": payload.sensors.consumed_g,
            "photos_count": payload.media.captured,
            "media_urls": payload.media.urls,
            "wifi_rssi_dbm": payload.device_status.wifi_rssi_dbm,
            "firmware_version": payload.device_status.firmware_version,
            "raw_payload": data,
            "ingested_at": datetime.now(timezone.utc),
        }

        inserted = await IotEventRepository.insert_event(doc)
        if not inserted:
            logger.info("Duplicate event_id=%s ignored", payload.event_id)
            return

        async with AsyncSessionLocal() as session:
            await DeviceRepository.update_last_seen(session, UUID(device_id))

    @staticmethod
    async def process_telemetry(device_id: str, raw: bytes) -> None:
        try:
            data = _decoder.decode(raw.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error("MQTT JSON decode error on telemetry topic device=%s: %s", device_id, exc)
            return

        try:
            payload = TelemetryPayload.model_validate(data)
        except Exception as exc:
            logger.warning("MQTT telemetry validation error device=%s: %s", device_id, exc)
            return

        async with AsyncSessionLocal() as session:
            device = await DeviceRepository.find_by_id(session, UUID(device_id))

        if device is None:
            logger.warning("Telemetry from unknown device_id=%s", device_id)
            return

        doc = {
            "device_id": device_id,
            "station_id": str(device.station_id) if device.station_id else None,
            "timestamp": payload.timestamp,
            "temperature_c": payload.sensors.temperature_c if payload.sensors else None,
            "humidity_pct": payload.sensors.humidity_pct if payload.sensors else None,
            "wifi_rssi_dbm": payload.device_status.wifi_rssi_dbm if payload.device_status else None,
            "firmware_version": payload.device_status.firmware_version if payload.device_status else None,
            "battery_pct": payload.device_status.battery_pct if payload.device_status else None,
            "ingested_at": datetime.now(timezone.utc),
        }

        await IotEventRepository.insert_telemetry(doc)

        async with AsyncSessionLocal() as session:
            await DeviceRepository.update_last_seen(session, UUID(device_id))

    @staticmethod
    async def process_status(device_id: str, raw: bytes) -> None:
        try:
            data = _decoder.decode(raw.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error("MQTT JSON decode error on status topic device=%s: %s", device_id, exc)
            return

        try:
            payload = StatusPayload.model_validate(data)
        except Exception as exc:
            logger.warning("MQTT status validation error device=%s: %s", device_id, exc)
            return

        async with AsyncSessionLocal() as session:
            device = await DeviceRepository.find_by_id(session, UUID(device_id))

        if device is None:
            logger.warning("Status from unknown device_id=%s", device_id)
            return

        station_id = str(device.station_id) if device.station_id else None

        if payload.status == "offline":
            async with AsyncSessionLocal() as session:
                await DeviceRepository.set_offline(session, UUID(device_id))
            if station_id:
                await AlertService.raise_alert(
                    alert_type=AlertType.connectivity_lost,
                    station_id=station_id,
                    device_id=device_id,
                    message=f"Device {device_id} went offline",
                )
        elif payload.status == "online":
            async with AsyncSessionLocal() as session:
                await DeviceRepository.set_online(session, UUID(device_id))
            if station_id:
                await AlertService.resolve_open_alerts(station_id, AlertType.connectivity_lost)
