"""Unit tests for GEO-4 aggregation methods: compute_station_animals, build_activity_feed."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.geoportal.aggregation import GeoportalAggregationService
from modules.geoportal.schemas import ActivityItemType, GeoportalAnimalRead
from shared.enums import TimeFilter


def _now():
    return datetime.now(timezone.utc)


def _make_animal(rfid_tag: str, species: str = "Cervidae", sex_value: str = "female"):
    a = MagicMock()
    a.id = uuid.uuid4()
    a.rfid_tag = rfid_tag
    a.species = species
    sex = MagicMock()
    sex.value = sex_value
    a.sex = sex
    a.estimated_age = "2-3 años"
    a.notes = None
    a.created_at = _now()
    return a


@pytest.fixture
def session():
    return AsyncMock()


# ─── compute_station_animals ─────────────────────────────────────────────────


class TestComputeStationAnimals:
    async def test_returns_empty_when_no_rfid_tags(self, session):
        with patch(
            "modules.geoportal.repository.GeoportalRepository.get_rfid_tags_for_station",
            new=AsyncMock(return_value=[]),
        ):
            result = await GeoportalAggregationService.compute_station_animals(
                session, "station-1", TimeFilter.d7
            )

        assert result == []

    async def test_returns_animals_sorted_by_visit_count_desc(self, session):
        station_id = "station-abc"
        tags = ["TAG-001", "TAG-002"]
        animal_a = _make_animal("TAG-001", species="Cervidae")
        animal_b = _make_animal("TAG-002", species="Tayassuidae")

        rfid_stats = {
            "TAG-001": {"count": 3, "last_visit": _now(), "avg_consumed_g": 120.0},
            "TAG-002": {"count": 10, "last_visit": _now(), "avg_consumed_g": 85.5},
        }

        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_rfid_tags_for_station",
                new=AsyncMock(return_value=tags),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animals_by_rfid_tags",
                new=AsyncMock(return_value=[animal_a, animal_b]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animal_rfid_stats",
                new=AsyncMock(return_value=rfid_stats),
            ),
        ):
            result = await GeoportalAggregationService.compute_station_animals(
                session, station_id, TimeFilter.d7
            )

        assert len(result) == 2
        assert isinstance(result[0], GeoportalAnimalRead)
        # TAG-002 has 10 visits → should be first
        assert result[0].rfid_tag == "TAG-002"
        assert result[0].total_visits == 10
        assert result[0].avg_consumed_g == 85.5
        # TAG-001 has 3 visits → second
        assert result[1].rfid_tag == "TAG-001"
        assert result[1].total_visits == 3
        assert result[1].avg_consumed_g == 120.0

    async def test_animal_with_no_stats_defaults_to_zero(self, session):
        animal = _make_animal("TAG-XYZ")

        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_rfid_tags_for_station",
                new=AsyncMock(return_value=["TAG-XYZ"]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animals_by_rfid_tags",
                new=AsyncMock(return_value=[animal]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animal_rfid_stats",
                new=AsyncMock(return_value={}),  # no stats for this tag
            ),
        ):
            result = await GeoportalAggregationService.compute_station_animals(
                session, "station-1", TimeFilter.d7
            )

        assert len(result) == 1
        assert result[0].total_visits == 0
        assert result[0].last_visit is None
        assert result[0].avg_consumed_g is None

    async def test_avg_consumed_g_is_rounded_to_one_decimal(self, session):
        animal = _make_animal("TAG-R")
        rfid_stats = {
            "TAG-R": {"count": 5, "last_visit": _now(), "avg_consumed_g": 123.456789},
        }

        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_rfid_tags_for_station",
                new=AsyncMock(return_value=["TAG-R"]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animals_by_rfid_tags",
                new=AsyncMock(return_value=[animal]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animal_rfid_stats",
                new=AsyncMock(return_value=rfid_stats),
            ),
        ):
            result = await GeoportalAggregationService.compute_station_animals(
                session, "station-1", TimeFilter.h24
            )

        assert result[0].avg_consumed_g == 123.5

    async def test_rfid_tags_not_registered_as_animals_are_ignored(self, session):
        """RFID tags seen in events but not in the animals table → silently dropped."""
        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_rfid_tags_for_station",
                new=AsyncMock(return_value=["UNKNOWN-TAG"]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animals_by_rfid_tags",
                new=AsyncMock(return_value=[]),  # not in PG
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animal_rfid_stats",
                new=AsyncMock(return_value={"UNKNOWN-TAG": {"count": 7}}),
            ),
        ):
            result = await GeoportalAggregationService.compute_station_animals(
                session, "station-1", TimeFilter.d7
            )

        assert result == []


# ─── build_activity_feed ─────────────────────────────────────────────────────


class TestBuildActivityFeed:
    async def test_returns_empty_when_no_data(self):
        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_iot_events_for_activity",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_alerts_for_activity",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_latest_telemetry_for_station",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await GeoportalAggregationService.build_activity_feed("station-1")

        assert result == []

    async def test_iot_event_with_rfid_emits_rfid_read_item(self):
        ts = _now()
        iot_doc = {
            "station_id": "station-1",
            "rfid_tag": "RFID-99",
            "consumed_g": 95.0,
            "ingested_at": ts,
            "media_urls": [],
            "photos_count": 0,
        }
        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_iot_events_for_activity",
                new=AsyncMock(return_value=[iot_doc]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_alerts_for_activity",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_latest_telemetry_for_station",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await GeoportalAggregationService.build_activity_feed("station-1")

        assert len(result) == 1
        item = result[0]
        assert item.item_type == ActivityItemType.rfid_read
        assert item.rfid_tag == "RFID-99"
        assert "RFID-99" in item.description
        assert "95" in item.description  # consumed_g formatted

    async def test_iot_event_without_rfid_emits_feeding_item(self):
        ts = _now()
        iot_doc = {
            "station_id": "station-1",
            "rfid_tag": None,
            "consumed_g": 200.0,
            "ingested_at": ts,
            "media_urls": [],
            "photos_count": 0,
        }
        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_iot_events_for_activity",
                new=AsyncMock(return_value=[iot_doc]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_alerts_for_activity",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_latest_telemetry_for_station",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await GeoportalAggregationService.build_activity_feed("station-1")

        assert len(result) == 1
        assert result[0].item_type == ActivityItemType.feeding
        assert result[0].rfid_tag is None

    async def test_event_with_media_emits_extra_photo_item(self):
        ts = _now()
        iot_doc = {
            "station_id": "station-1",
            "rfid_tag": "RFID-A",
            "consumed_g": 50.0,
            "ingested_at": ts,
            "media_urls": ["https://cdn.example.com/photo.jpg"],
            "photos_count": 1,
        }
        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_iot_events_for_activity",
                new=AsyncMock(return_value=[iot_doc]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_alerts_for_activity",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_latest_telemetry_for_station",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await GeoportalAggregationService.build_activity_feed("station-1")

        types = [item.item_type for item in result]
        assert ActivityItemType.rfid_read in types
        assert ActivityItemType.photo in types

    async def test_alert_doc_emits_alert_item(self):
        ts = _now()
        alert_doc = {
            "station_id": "station-1",
            "alert_type": "empty_tank",
            "severity": "critical",
            "created_at": ts,
        }
        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_iot_events_for_activity",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_alerts_for_activity",
                new=AsyncMock(return_value=[alert_doc]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_latest_telemetry_for_station",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await GeoportalAggregationService.build_activity_feed("station-1")

        assert len(result) == 1
        item = result[0]
        assert item.item_type == ActivityItemType.alert
        assert item.severity == "critical"
        assert "empty_tank" in item.description

    async def test_telemetry_doc_emits_telemetry_item(self):
        ts = _now()
        telemetry_doc = {
            "station_id": "station-1",
            "temperature_c": 28.5,
            "humidity_pct": 72.0,
            "ingested_at": ts,
        }
        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_iot_events_for_activity",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_alerts_for_activity",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_latest_telemetry_for_station",
                new=AsyncMock(return_value=telemetry_doc),
            ),
        ):
            result = await GeoportalAggregationService.build_activity_feed("station-1")

        assert len(result) == 1
        item = result[0]
        assert item.item_type == ActivityItemType.telemetry
        assert "28.5" in item.description
        assert "72" in item.description

    async def test_feed_is_sorted_by_timestamp_desc(self):
        early = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        late = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

        iot_doc = {
            "station_id": "s",
            "rfid_tag": None,
            "consumed_g": 10.0,
            "ingested_at": early,
            "media_urls": [],
            "photos_count": 0,
        }
        alert_doc = {
            "station_id": "s",
            "alert_type": "sensor_failure",
            "severity": "warning",
            "created_at": late,
        }
        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_iot_events_for_activity",
                new=AsyncMock(return_value=[iot_doc]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_alerts_for_activity",
                new=AsyncMock(return_value=[alert_doc]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_latest_telemetry_for_station",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await GeoportalAggregationService.build_activity_feed("station-1")

        # Most recent first
        assert result[0].timestamp == late
        assert result[1].timestamp == early

    async def test_limit_is_respected(self):
        ts = _now()
        iot_docs = [
            {
                "station_id": "s",
                "rfid_tag": None,
                "consumed_g": float(i),
                "ingested_at": ts,
                "media_urls": [],
                "photos_count": 0,
            }
            for i in range(15)
        ]
        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_iot_events_for_activity",
                new=AsyncMock(return_value=iot_docs),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_alerts_for_activity",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_latest_telemetry_for_station",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await GeoportalAggregationService.build_activity_feed(
                "station-1", limit=5
            )

        assert len(result) == 5

    async def test_iot_doc_without_datetime_timestamp_is_skipped(self):
        iot_doc = {
            "station_id": "s",
            "rfid_tag": "X",
            "consumed_g": 10.0,
            "ingested_at": "not-a-datetime",  # string, not datetime
            "media_urls": [],
            "photos_count": 0,
        }
        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_iot_events_for_activity",
                new=AsyncMock(return_value=[iot_doc]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_recent_alerts_for_activity",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_latest_telemetry_for_station",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await GeoportalAggregationService.build_activity_feed("station-1")

        assert result == []
