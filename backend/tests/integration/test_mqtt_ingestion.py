"""
End-to-end MQTT ingestion integration tests.

Requires:
  - Running Mosquitto on localhost:1883
  - Running MongoDB on localhost:27017
  - Running PostgreSQL with migrations at head
  - RUN_MQTT_INTEGRATION_TESTS=1

Run with:
  RUN_MQTT_INTEGRATION_TESTS=1 pytest tests/integration/test_mqtt_ingestion.py -v
"""
import asyncio
import json
import os
import time
import uuid

import aiomqtt
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from infrastructure.mongodb import database, COLLECTION_IOT_EVENTS, COLLECTION_ALERTS
from shared.config import get_settings

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_MQTT_INTEGRATION_TESTS") != "1",
    reason="Set RUN_MQTT_INTEGRATION_TESTS=1 and start Mosquitto + MongoDB + PostgreSQL.",
)

settings = get_settings()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _publish(topic: str, payload: dict) -> None:
    async with aiomqtt.Client(
        hostname=settings.mqtt_host,
        port=settings.mqtt_port,
        identifier=f"test-publisher-{uuid.uuid4().hex[:8]}",
    ) as client:
        await client.publish(topic, json.dumps(payload), qos=1)


def _pub(topic: str, payload: dict) -> None:
    asyncio.run(_publish(topic, payload))


async def _find_event(event_id: str) -> dict | None:
    return await database[COLLECTION_IOT_EVENTS].find_one({"event_id": event_id})


async def _count_events(event_id: str) -> int:
    return await database[COLLECTION_IOT_EVENTS].count_documents({"event_id": event_id})


async def _find_alert(station_id: str, alert_type: str) -> dict | None:
    return await database[COLLECTION_ALERTS].find_one(
        {"station_id": station_id, "alert_type": alert_type}
    )


def _register_and_get_token(client: TestClient) -> tuple[str, str]:
    email = f"mqtt-test-{time.time_ns()}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"name": "MQTT Tester", "document": "99999", "email": email, "password": "SecurePass1"},
    )
    assert r.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass1"})
    assert login.status_code == 200
    return login.json()["access_token"], email


def _create_zone(client: TestClient, token: str) -> str:
    r = client.post(
        "/api/v1/zones",
        json={"name": f"MQTT Zone {uuid.uuid4().hex[:6]}", "city": "Bogotá", "country": "CO",
              "latitude": 4.6, "longitude": -74.1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    return r.json()["id"]


def _create_station(client: TestClient, token: str, zone_id: str) -> str:
    r = client.post(
        "/api/v1/stations",
        json={"code": f"MQTT{uuid.uuid4().hex[:6].upper()}", "name": "MQTT Station",
              "zone_id": zone_id, "latitude": 4.6, "longitude": -74.1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    return r.json()["id"]


def _register_device(client: TestClient, token: str, station_id: str) -> str:
    r = client.post(
        "/api/v1/devices",
        json={
            "serial_number": f"SN-{uuid.uuid4().hex[:10].upper()}",
            "name": "Test ESP32",
            "station_id": station_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(), raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="module")
def setup(client):
    token, _ = _register_and_get_token(client)
    zone_id = _create_zone(client, token)
    station_id = _create_station(client, token, zone_id)
    device_id = _register_device(client, token, station_id)
    return {"token": token, "station_id": station_id, "device_id": device_id}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMqttFeedingEvent:
    def test_feeding_event_stored_in_mongodb(self, setup):
        device_id = setup["device_id"]
        station_id = setup["station_id"]
        event_id = str(uuid.uuid4())

        _pub(
            f"wildtrack/devices/{device_id}/events",
            {
                "event_id": event_id,
                "event_type": "feeding_session",
                "device_id": device_id,
                "timestamp": "2024-01-01T12:00:00Z",
                "rfid": {"detected": False, "tag": None, "read_quality": None},
                "sensors": {
                    "temperature_c": 22.5, "humidity_pct": 68.0,
                    "initial_weight_g": 500.0, "final_weight_g": 420.0, "consumed_g": 80.0,
                },
                "media": {"captured": 0, "urls": []},
                "device_status": {"wifi_rssi_dbm": -62, "firmware_version": "1.2.0", "battery_pct": None},
            },
        )
        time.sleep(1)

        doc = asyncio.run(_find_event(event_id))
        assert doc is not None, "Event not found in MongoDB"
        assert doc["device_id"] == device_id
        assert doc["station_id"] == station_id
        assert doc["station_code"] is not None
        assert doc["zone_id"] is not None

    def test_duplicate_event_id_is_ignored(self, setup):
        device_id = setup["device_id"]
        event_id = str(uuid.uuid4())

        payload = {
            "event_id": event_id,
            "event_type": "feeding_session",
            "device_id": device_id,
            "timestamp": "2024-01-01T12:01:00Z",
            "rfid": {"detected": False, "tag": None, "read_quality": None},
            "sensors": {
                "temperature_c": 22.0, "humidity_pct": 65.0,
                "initial_weight_g": 400.0, "final_weight_g": 380.0, "consumed_g": 20.0,
            },
            "media": {"captured": 0, "urls": []},
            "device_status": {"wifi_rssi_dbm": -60, "firmware_version": "1.2.0", "battery_pct": None},
        }
        _pub(f"wildtrack/devices/{device_id}/events", payload)
        _pub(f"wildtrack/devices/{device_id}/events", payload)
        time.sleep(1)

        count = asyncio.run(_count_events(event_id))
        assert count == 1, f"Expected 1 document, got {count}"

    def test_rfid_hardware_failure_creates_alert(self, setup):
        device_id = setup["device_id"]
        station_id = setup["station_id"]
        event_id = str(uuid.uuid4())

        _pub(
            f"wildtrack/devices/{device_id}/events",
            {
                "event_id": event_id,
                "event_type": "feeding_session",
                "device_id": device_id,
                "timestamp": "2024-01-01T12:02:00Z",
                "rfid": {"detected": True, "tag": None, "read_quality": "retry"},
                "sensors": {
                    "temperature_c": 22.0, "humidity_pct": 65.0,
                    "initial_weight_g": 400.0, "final_weight_g": 400.0, "consumed_g": 0.0,
                },
                "media": {"captured": 0, "urls": []},
                "device_status": {"wifi_rssi_dbm": -60, "firmware_version": "1.2.0", "battery_pct": None},
            },
        )
        time.sleep(1)

        alert = asyncio.run(_find_alert(station_id, "rfid_read_failure"))
        assert alert is not None, "rfid_read_failure alert not found"
        assert alert["resolved"] is False


class TestMqttStatusLwt:
    def test_offline_status_creates_connectivity_alert(self, setup):
        device_id = setup["device_id"]
        station_id = setup["station_id"]

        _pub(
            f"wildtrack/devices/{device_id}/status",
            {"device_id": device_id, "status": "offline", "timestamp": "2024-01-01T12:10:00Z"},
        )
        time.sleep(1)

        alert = asyncio.run(_find_alert(station_id, "connectivity_lost"))
        assert alert is not None, "connectivity_lost alert not found"
        assert alert["resolved"] is False

    def test_online_status_resolves_connectivity_alert(self, setup):
        device_id = setup["device_id"]
        station_id = setup["station_id"]

        _pub(
            f"wildtrack/devices/{device_id}/status",
            {"device_id": device_id, "status": "online", "timestamp": "2024-01-01T12:11:00Z"},
        )
        time.sleep(1)

        alert = asyncio.run(_find_alert(station_id, "connectivity_lost"))
        assert alert is not None
        assert alert["resolved"] is True
