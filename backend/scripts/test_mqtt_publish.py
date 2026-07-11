"""
MQTT test publisher — simulates an ESP32 device.

Usage:
  python scripts/test_mqtt_publish.py --device-id <uuid> --event feeding_session
  python scripts/test_mqtt_publish.py --device-id <uuid> --event rfid_failure
  python scripts/test_mqtt_publish.py --device-id <uuid> --event offline
  python scripts/test_mqtt_publish.py --device-id <uuid> --event online
  python scripts/test_mqtt_publish.py --device-id <uuid> --event telemetry
  python scripts/test_mqtt_publish.py --device-id <uuid> --event unknown_device

No physical ESP32 needed. Run this against a local Mosquitto broker.
"""
import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone

import aiomqtt

from shared.config import get_settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _feeding_session(device_id: str) -> tuple[str, dict]:
    topic = f"wildtrack/devices/{device_id}/events"
    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "feeding_session",
        "device_id": device_id,
        "timestamp": _now(),
        "rfid": {"detected": True, "tag": "RFID-TEST-001", "read_quality": "good"},
        "sensors": {
            "temperature_c": 22.5,
            "humidity_pct": 68.0,
            "initial_weight_g": 500.0,
            "final_weight_g": 420.0,
            "consumed_g": 80.0,
        },
        "media": {"captured": 1, "urls": []},
        "device_status": {
            "wifi_rssi_dbm": -62,
            "firmware_version": "1.2.0",
            "battery_pct": 85.0,
        },
    }
    return topic, payload


def _rfid_failure(device_id: str) -> tuple[str, dict]:
    topic = f"wildtrack/devices/{device_id}/events"
    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "feeding_session",
        "device_id": device_id,
        "timestamp": _now(),
        "rfid": {"detected": True, "tag": None, "read_quality": "retry"},
        "sensors": {
            "temperature_c": 22.0,
            "humidity_pct": 65.0,
            "initial_weight_g": 400.0,
            "final_weight_g": 400.0,
            "consumed_g": 0.0,
        },
        "media": {"captured": 0, "urls": []},
        "device_status": {"wifi_rssi_dbm": -70, "firmware_version": "1.2.0", "battery_pct": None},
    }
    return topic, payload


def _telemetry(device_id: str) -> tuple[str, dict]:
    topic = f"wildtrack/devices/{device_id}/telemetry"
    payload = {
        "device_id": device_id,
        "timestamp": _now(),
        "sensors": {"temperature_c": 21.8, "humidity_pct": 70.0},
        "device_status": {"wifi_rssi_dbm": -55, "firmware_version": "1.2.0", "battery_pct": 90.0},
    }
    return topic, payload


def _offline(device_id: str) -> tuple[str, dict]:
    topic = f"wildtrack/devices/{device_id}/status"
    payload = {"device_id": device_id, "status": "offline", "timestamp": _now()}
    return topic, payload


def _online(device_id: str) -> tuple[str, dict]:
    topic = f"wildtrack/devices/{device_id}/status"
    payload = {"device_id": device_id, "status": "online", "timestamp": _now()}
    return topic, payload


def _unknown_device(_device_id: str) -> tuple[str, dict]:
    fake_id = str(uuid.uuid4())
    topic = f"wildtrack/devices/{fake_id}/events"
    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "feeding_session",
        "device_id": fake_id,
        "timestamp": _now(),
        "rfid": {"detected": False, "tag": None, "read_quality": None},
        "sensors": {
            "temperature_c": 20.0, "humidity_pct": 60.0,
            "initial_weight_g": 300.0, "final_weight_g": 280.0, "consumed_g": 20.0,
        },
        "media": {"captured": 0, "urls": []},
        "device_status": {"wifi_rssi_dbm": -80, "firmware_version": "1.2.0", "battery_pct": None},
    }
    print(f"  [unknown_device] publishing with fake device_id={fake_id}")
    return topic, payload


EVENTS = {
    "feeding_session": _feeding_session,
    "rfid_failure": _rfid_failure,
    "telemetry": _telemetry,
    "offline": _offline,
    "online": _online,
    "unknown_device": _unknown_device,
}


async def publish(device_id: str, event: str, host: str, port: int) -> None:
    settings = get_settings()
    builder = EVENTS[event]
    topic, payload = builder(device_id)

    print(f"  topic   : {topic}")
    print(f"  payload : {json.dumps(payload, indent=2, default=str)}")

    mqtt_kwargs: dict = {}
    if settings.mqtt_username:
        mqtt_kwargs["username"] = settings.mqtt_username
        mqtt_kwargs["password"] = settings.mqtt_password

    async with aiomqtt.Client(
        hostname=host,
        port=port,
        identifier=f"wildtrack-test-{uuid.uuid4().hex[:8]}",
        **mqtt_kwargs,
    ) as client:
        await client.publish(topic, json.dumps(payload, default=str), qos=1)

    print("\n✓ Message published. Check backend logs and MongoDB.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate ESP32 MQTT publish")
    parser.add_argument("--device-id", required=True, help="UUID of a registered device")
    parser.add_argument(
        "--event",
        required=True,
        choices=list(EVENTS.keys()),
        help="Event type to publish",
    )
    parser.add_argument("--host", default=None, help="MQTT broker host (default: from .env)")
    parser.add_argument("--port", default=None, type=int, help="MQTT broker port (default: from .env)")
    args = parser.parse_args()

    settings = get_settings()
    host = args.host or settings.mqtt_host
    port = args.port or settings.mqtt_port

    print(f"\n→ Publishing '{args.event}' for device {args.device_id} to {host}:{port}\n")
    asyncio.run(publish(args.device_id, args.event, host, port))


if __name__ == "__main__":
    main()
