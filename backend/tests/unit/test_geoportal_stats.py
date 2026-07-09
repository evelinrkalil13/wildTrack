"""Unit tests for GEO-5/GEO-6 aggregation."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.geoportal.aggregation import (
    GeoportalAggregationService,
    StationCounts,
    _dedup_consecutive,
)
from modules.geoportal.schemas import AnimalHistoryResponse, AnimalMovement, SectorStatRow
from shared.enums import TimeFilter


def _make_station_row(
    station_id=None,
    zone_id=None,
    zone_name="Zona Norte",
    zone_color="#52b788",
    station_name="Comedero Norte",
    station_code="STA-001",
    status_val=None,
):
    row = MagicMock()
    row.station_id = station_id or uuid.uuid4()
    row.station_code = station_code
    row.station_name = station_name
    row.zone_id = zone_id or uuid.uuid4()
    row.zone_name = zone_name
    row.zone_color = zone_color
    return row


def _make_animal(rfid_tag: str, species: str = "Cervidae", sex_value: str = "female"):
    a = MagicMock()
    a.id = uuid.uuid4()
    a.rfid_tag = rfid_tag
    a.species = species
    sex = MagicMock()
    sex.value = sex_value
    a.sex = sex
    return a


# ─── _dedup_consecutive ──────────────────────────────────────────────────────


def test_dedup_consecutive_removes_adjacent_dupes():
    assert _dedup_consecutive(["A", "A", "B", "B", "A"]) == ["A", "B", "A"]


def test_dedup_consecutive_empty():
    assert _dedup_consecutive([]) == []


def test_dedup_consecutive_no_dupes():
    assert _dedup_consecutive(["A", "B", "C"]) == ["A", "B", "C"]


# ─── compute_sector_summaries ────────────────────────────────────────────────


class TestComputeSectorSummaries:
    def _make_inputs(self, same_zone=True):
        zone_id = uuid.uuid4()
        zone2_id = uuid.uuid4()
        sid1 = uuid.uuid4()
        sid2 = uuid.uuid4()
        row1 = _make_station_row(station_id=sid1, zone_id=zone_id, zone_name="NORTE", zone_color="#52b788")
        if same_zone:
            row2 = _make_station_row(station_id=sid2, zone_id=zone_id, zone_name="NORTE", zone_color="#52b788")
        else:
            row2 = _make_station_row(station_id=sid2, zone_id=zone2_id, zone_name="SUR", zone_color="#e08a1e")

        counts_map = {
            str(sid1): StationCounts(visitas_total=30, visitas_identificadas=20, visitas_sin_identificar=10),
            str(sid2): StationCounts(visitas_total=20, visitas_identificadas=15, visitas_sin_identificar=5),
        }
        alert_map = {str(sid1): 2, str(sid2): 0}
        avg_weights = {str(sid1): 100.0, str(sid2): 80.0}
        return [row1, row2], counts_map, alert_map, avg_weights, str(zone_id), str(zone2_id)

    def test_single_zone_aggregates_all_stations(self):
        rows, counts, alerts, weights, zone_id, _ = self._make_inputs(same_zone=True)
        result = GeoportalAggregationService.compute_sector_summaries(rows, counts, alerts, weights)

        assert len(result) == 1
        sector = result[0]
        assert isinstance(sector, SectorStatRow)
        assert sector.num_estaciones == 2
        assert sector.visitas == 50
        assert sector.identificados == 35
        assert sector.sin_identificar == 15
        assert sector.en_alerta == 1  # only sid1 has open alerts

    def test_pct_sin_id_calculated_correctly(self):
        rows, counts, alerts, weights, _, _ = self._make_inputs(same_zone=True)
        result = GeoportalAggregationService.compute_sector_summaries(rows, counts, alerts, weights)
        # 15 out of 50 = 30%
        assert result[0].pct_sin_id == 30.0

    def test_weighted_avg_weight(self):
        rows, counts, alerts, weights, _, _ = self._make_inputs(same_zone=True)
        result = GeoportalAggregationService.compute_sector_summaries(rows, counts, alerts, weights)
        # (100 * 30 + 80 * 20) / (30 + 20) = (3000 + 1600) / 50 = 92.0
        assert result[0].peso_promedio_g == 92.0

    def test_two_zones_returns_two_rows(self):
        rows, counts, alerts, weights, _, _ = self._make_inputs(same_zone=False)
        result = GeoportalAggregationService.compute_sector_summaries(rows, counts, alerts, weights)
        assert len(result) == 2

    def test_sorted_by_visitas_desc(self):
        rows, counts, alerts, weights, _, _ = self._make_inputs(same_zone=False)
        result = GeoportalAggregationService.compute_sector_summaries(rows, counts, alerts, weights)
        assert result[0].visitas >= result[1].visitas

    def test_zero_visits_no_weight(self):
        sid = uuid.uuid4()
        row = _make_station_row(station_id=sid)
        result = GeoportalAggregationService.compute_sector_summaries(
            [row], {}, {}, {}
        )
        assert result[0].visitas == 0
        assert result[0].pct_sin_id == 0.0
        assert result[0].peso_promedio_g is None


# ─── compute_animal_movements ────────────────────────────────────────────────


class TestComputeAnimalMovements:
    def test_returns_empty_when_no_animals(self):
        result = GeoportalAggregationService.compute_animal_movements([], {}, {})
        assert result == []

    def test_single_animal_single_station(self):
        animal = _make_animal("RFID-A")
        sid = str(uuid.uuid4())
        paths_map = {"RFID-A": [sid, sid, sid]}  # repeated same station
        station_name_map = {sid: "Comedero Norte"}

        result = GeoportalAggregationService.compute_animal_movements(
            [animal], paths_map, station_name_map
        )

        assert len(result) == 1
        mv = result[0]
        assert isinstance(mv, AnimalMovement)
        assert mv.rfid_tag == "RFID-A"
        assert mv.distinct_stations == 1
        assert mv.path == [sid]
        assert mv.path_names == ["Comedero Norte"]

    def test_animal_with_multiple_stations(self):
        animal = _make_animal("RFID-B")
        s1, s2, s3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        paths_map = {"RFID-B": [s1, s1, s2, s3, s1]}
        station_name_map = {s1: "Norte", s2: "Sur", s3: "Este"}

        result = GeoportalAggregationService.compute_animal_movements(
            [animal], paths_map, station_name_map
        )

        mv = result[0]
        assert mv.distinct_stations == 3
        # deduped path: [s1, s2, s3, s1]
        assert mv.path == [s1, s2, s3, s1]
        assert mv.path_names == ["Norte", "Sur", "Este", "Norte"]

    def test_sorted_by_distinct_stations_desc(self):
        a1 = _make_animal("RFID-X")
        a2 = _make_animal("RFID-Y")
        s1, s2, s3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        paths_map = {
            "RFID-X": [s1, s2, s3],  # 3 distinct
            "RFID-Y": [s1],           # 1 distinct
        }
        result = GeoportalAggregationService.compute_animal_movements(
            [a1, a2], paths_map, {}
        )
        assert result[0].rfid_tag == "RFID-X"
        assert result[1].rfid_tag == "RFID-Y"

    def test_animal_with_no_path_has_zero_distinct(self):
        animal = _make_animal("RFID-Z")
        result = GeoportalAggregationService.compute_animal_movements(
            [animal], {}, {}
        )
        assert result[0].distinct_stations == 0
        assert result[0].path == []


# ─── compute_animal_history ──────────────────────────────────────────────────


def _make_station_row_with_coords(station_id=None, lat=4.71, lng=-74.07, station_name="Norte"):
    row = _make_station_row(station_id=station_id, station_name=station_name)
    row.latitude = lat
    row.longitude = lng
    return row


def _make_iot_doc(station_id: str, consumed_g: float = 200.0, days_ago: int = 1) -> dict:
    from datetime import timedelta
    ts = datetime(2026, 7, 9, 10, 0, 0, tzinfo=timezone.utc) - timedelta(days=days_ago)
    return {
        "event_id": str(uuid.uuid4()),
        "station_id": station_id,
        "rfid_tag": "RFID-TEST",
        "consumed_g": consumed_g,
        "temperature_c": 25.0,
        "humidity_pct": 70.0,
        "media_urls": [],
        "ingested_at": ts,
    }


class TestComputeAnimalHistory:
    def _make_animal(self, rfid_tag: str = "RFID-TEST"):
        a = MagicMock()
        a.id = uuid.uuid4()
        a.rfid_tag = rfid_tag
        a.species = "Oso hormiguero"
        sex = MagicMock()
        sex.value = "male"
        a.sex = sex
        a.estimated_age = "adult"
        a.notes = None
        return a

    async def test_basic_kpis_single_station(self):
        animal = self._make_animal()
        sid = str(uuid.uuid4())
        docs = [_make_iot_doc(sid, 200.0, 1), _make_iot_doc(sid, 180.0, 2)]
        rows = [_make_station_row_with_coords(station_id=uuid.UUID(sid))]

        with (
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_feeding_timeline", new=AsyncMock(return_value=docs)),
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_weekly_activity", new=AsyncMock(return_value=[0, 2, 0, 0, 0, 0, 0])),
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_station_visit_counts", new=AsyncMock(return_value={sid: 2})),
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_station_paths", new=AsyncMock(return_value={"RFID-TEST": [sid, sid]})),
        ):
            result = await GeoportalAggregationService.compute_animal_history(
                animal, TimeFilter.all, rows
            )

        assert isinstance(result, AnimalHistoryResponse)
        assert result.total_alimentaciones == 2
        assert result.total_estaciones == 1
        assert result.dias_activo >= 1
        assert result.peso_promedio_g == 190.0
        assert result.actividad_semanal == [0, 2, 0, 0, 0, 0, 0]

    async def test_insight_text_preference_when_dominant_station(self):
        animal = self._make_animal()
        s1, s2 = str(uuid.uuid4()), str(uuid.uuid4())
        docs = [_make_iot_doc(s1, 200.0, i) for i in range(7)] + [_make_iot_doc(s2, 150.0, 8)]
        rows = [
            _make_station_row_with_coords(station_id=uuid.UUID(s1), station_name="Comedero Norte"),
            _make_station_row_with_coords(station_id=uuid.UUID(s2), station_name="Comedero Sur"),
        ]

        with (
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_feeding_timeline", new=AsyncMock(return_value=docs)),
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_weekly_activity", new=AsyncMock(return_value=[1]*7)),
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_station_visit_counts", new=AsyncMock(return_value={s1: 7, s2: 1})),
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_station_paths", new=AsyncMock(return_value={"RFID-TEST": [s1]*7 + [s2]})),
        ):
            result = await GeoportalAggregationService.compute_animal_history(
                animal, TimeFilter.all, rows
            )

        assert "Preferencia marcada" in result.insight_text
        assert "Comedero Norte" in result.insight_text

    async def test_zero_events_returns_empty_history(self):
        animal = self._make_animal()

        with (
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_feeding_timeline", new=AsyncMock(return_value=[])),
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_weekly_activity", new=AsyncMock(return_value=[0]*7)),
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_station_visit_counts", new=AsyncMock(return_value={})),
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_station_paths", new=AsyncMock(return_value={})),
        ):
            result = await GeoportalAggregationService.compute_animal_history(
                animal, TimeFilter.all, []
            )

        assert result.total_alimentaciones == 0
        assert result.total_estaciones == 0
        assert result.dias_activo == 0
        assert result.peso_promedio_g is None
        assert result.feeder_ranking == []
        assert result.timeline == []
        assert result.trace_path == []
        assert result.insight_text == "Registrado en un único comedero"

    async def test_trace_path_uses_deduped_stations(self):
        animal = self._make_animal()
        s1, s2 = str(uuid.uuid4()), str(uuid.uuid4())
        now = datetime(2026, 7, 8, 10, 0, 0, tzinfo=timezone.utc)
        docs = [
            {**_make_iot_doc(s1, 200.0, 1), "ingested_at": now},
            {**_make_iot_doc(s2, 180.0, 2), "ingested_at": now},
        ]
        rows = [
            _make_station_row_with_coords(station_id=uuid.UUID(s1), station_name="Norte"),
            _make_station_row_with_coords(station_id=uuid.UUID(s2), station_name="Sur"),
        ]

        # raw path: s1, s1, s2, s1 → deduped: s1, s2, s1
        with (
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_feeding_timeline", new=AsyncMock(return_value=docs)),
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_weekly_activity", new=AsyncMock(return_value=[0]*7)),
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_station_visit_counts", new=AsyncMock(return_value={s1: 3, s2: 1})),
            patch("modules.geoportal.repository.GeoportalRepository.get_animal_station_paths", new=AsyncMock(return_value={"RFID-TEST": [s1, s1, s2, s1]})),
        ):
            result = await GeoportalAggregationService.compute_animal_history(
                animal, TimeFilter.all, rows
            )

        station_ids_in_trace = [stop.station_id for stop in result.trace_path]
        assert station_ids_in_trace == [s1, s2, s1]
        assert result.trace_path[0].lat == 4.71
        assert result.trace_path[0].lng == -74.07
