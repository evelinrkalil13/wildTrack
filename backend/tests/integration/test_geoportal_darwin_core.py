"""Integration tests for GET /api/v1/geoportal/animals/{animal_id}/darwin-core."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import create_app
from infrastructure.gbif_client import GbifTaxonomyData, clear_cache
from modules.geoportal.schemas import DarwinCoreResponse
from shared.enums import AnimalSex, UserRole


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_user(role: UserRole = UserRole.researcher) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    u.is_active = True
    return u


def _make_animal(
    animal_id=None,
    rfid_tag="TAG-001",
    species="Panthera onca",
    sex=AnimalSex.male,
    estimated_age="adulto",
    notes=None,
):
    a = MagicMock()
    a.id = animal_id or uuid.uuid4()
    a.rfid_tag = rfid_tag
    a.species = species
    a.sex = sex
    a.estimated_age = estimated_age
    a.notes = notes
    a.deleted_at = None
    return a


def _make_station(name="Comedero Norte", code="STA-001", lat=4.71, lng=-74.07):
    s = MagicMock()
    s.name = name
    s.code = code
    s.latitude = lat
    s.longitude = lng
    return s


def _make_zone(country="Colombia", city="Medellín", municipality="Itagüí"):
    z = MagicMock()
    z.country = country
    z.city = city
    z.municipality = municipality
    return z


GBIF_TAXONOMY_OK = GbifTaxonomyData(
    kingdom="Animalia",
    phylum="Chordata",
    taxon_class="Mammalia",
    order="Carnivora",
    family="Felidae",
    genus="Panthera",
    specific_epithet="onca",
    scientific_name="Panthera onca Linnaeus, 1758",
    scientific_name_authorship="Linnaeus, 1758",
    taxon_rank="SPECIES",
    vernacular_name="Jaguar",
    gbif_usage_key=5219404,
    gbif_confidence=99,
    gbif_match_type="EXACT",
)

IOT_EVENT = {
    "_id": "evt-001",
    "station_id": str(uuid.uuid4()),
    "rfid_tag": "TAG-001",
    "ingested_at": datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
}


@pytest.fixture(autouse=True)
def clear_gbif_cache():
    clear_cache()
    yield
    clear_cache()


# ── Helper to build TestClient with mocked auth ───────────────────────────────

def _client() -> TestClient:
    app = create_app()
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestDarwinCoreHappyPath:
    def test_returns_200_with_full_darwin_core(self):
        animal_id = str(uuid.uuid4())
        station = _make_station()
        zone = _make_zone()
        event = {**IOT_EVENT, "station_id": str(uuid.uuid4())}

        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animal_by_id",
                new=AsyncMock(return_value=_make_animal(animal_id=uuid.UUID(animal_id))),
            ),
            patch(
                "infrastructure.gbif_client.fetch_taxonomy",
                new=AsyncMock(return_value=(GBIF_TAXONOMY_OK, "ok")),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_last_rfid_event_for_animal",
                new=AsyncMock(return_value=event),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_station_with_zone",
                new=AsyncMock(return_value=(station, zone)),
            ),
        ):
            res = _client().get(
                f"/api/v1/geoportal/animals/{animal_id}/darwin-core",
                headers={"Authorization": "Bearer test"},
            )

        assert res.status_code == 200
        body = res.json()
        assert body["animal_id"] == animal_id
        assert body["species"] == "Panthera onca"
        assert body["source_status"] == "ok"

        tax = body["taxonomy"]
        assert tax["kingdom"] == "Animalia"
        assert tax["phylum"] == "Chordata"
        assert tax["taxon_class"] == "Mammalia"
        assert tax["order"] == "Carnivora"
        assert tax["family"] == "Felidae"
        assert tax["genus"] == "Panthera"
        assert tax["specific_epithet"] == "onca"
        assert tax["taxon_rank"] == "SPECIES"
        assert tax["vernacular_name"] == "Jaguar"
        assert tax["gbif_usage_key"] == 5219404
        assert tax["gbif_match_type"] == "EXACT"

        obs = body["observation"]
        assert obs["occurrence_id"] == animal_id
        assert obs["basis_of_record"] == "MachineObservation"
        assert obs["recorded_by"] == "WildTrack Biomonitoring System"
        assert obs["institution_code"] == "WildTrack"
        assert obs["collection_code"] == "BIOMONIT-ABR"
        assert obs["license"] == "CC BY-NC 4.0"
        assert obs["nomenclatural_code"] == "ICZN"
        assert obs["geodetic_datum"] == "WGS84"
        assert obs["coordinate_uncertainty_in_meters"] == 10
        assert obs["decimal_latitude"] == pytest.approx(4.71)
        assert obs["decimal_longitude"] == pytest.approx(-74.07)
        assert obs["country"] == "Colombia"
        assert obs["municipality"] == "Itagüí"
        assert obs["locality"] == "Comedero Norte"
        assert obs["individual_count"] == 1

        sources = body["sources"]
        assert sources["taxonomy"]["provider"] == "GBIF — Global Biodiversity Information Facility"
        assert sources["taxonomy"]["url"] == "https://www.gbif.org/species/5219404"
        assert sources["taxonomy"]["api_url"] == "https://api.gbif.org/v1/species/5219404"
        assert sources["taxonomy"]["license"] == "CC BY 4.0"
        assert sources["observation"]["provider"] == "WildTrack Biomonitoring System"
        assert "generated_at" in body

    def test_occurrence_id_is_animal_id(self):
        animal_id = str(uuid.uuid4())
        animal = _make_animal(animal_id=uuid.UUID(animal_id))

        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animal_by_id",
                new=AsyncMock(return_value=animal),
            ),
            patch(
                "infrastructure.gbif_client.fetch_taxonomy",
                new=AsyncMock(return_value=(GBIF_TAXONOMY_OK, "ok")),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_last_rfid_event_for_animal",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_station_with_zone",
                new=AsyncMock(return_value=None),
            ),
        ):
            res = _client().get(
                f"/api/v1/geoportal/animals/{animal_id}/darwin-core",
                headers={"Authorization": "Bearer test"},
            )

        assert res.status_code == 200
        obs = res.json()["observation"]
        assert obs["occurrence_id"] == animal_id


class TestDarwinCoreAnimalNotFound:
    def test_returns_404(self):
        animal_id = str(uuid.uuid4())

        with patch(
            "modules.geoportal.repository.GeoportalRepository.get_animal_by_id",
            new=AsyncMock(return_value=None),
        ):
            res = _client().get(
                f"/api/v1/geoportal/animals/{animal_id}/darwin-core",
                headers={"Authorization": "Bearer test"},
            )

        assert res.status_code == 404
        assert res.json()["detail"] == "Animal not found"


class TestDarwinCoreGbifUnavailable:
    def test_returns_200_with_unavailable_status_and_null_taxonomy(self):
        animal_id = str(uuid.uuid4())

        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animal_by_id",
                new=AsyncMock(return_value=_make_animal(animal_id=uuid.UUID(animal_id))),
            ),
            patch(
                "infrastructure.gbif_client.fetch_taxonomy",
                new=AsyncMock(return_value=(None, "unavailable")),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_last_rfid_event_for_animal",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_station_with_zone",
                new=AsyncMock(return_value=None),
            ),
        ):
            res = _client().get(
                f"/api/v1/geoportal/animals/{animal_id}/darwin-core",
                headers={"Authorization": "Bearer test"},
            )

        assert res.status_code == 200
        body = res.json()
        assert body["source_status"] == "unavailable"
        assert body["taxonomy"] is None
        assert body["sources"]["taxonomy"]["url"] is None
        assert body["sources"]["taxonomy"]["api_url"] is None

    def test_not_found_gbif_also_returns_200(self):
        animal_id = str(uuid.uuid4())

        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animal_by_id",
                new=AsyncMock(return_value=_make_animal(animal_id=uuid.UUID(animal_id))),
            ),
            patch(
                "infrastructure.gbif_client.fetch_taxonomy",
                new=AsyncMock(return_value=(None, "not_found")),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_last_rfid_event_for_animal",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_station_with_zone",
                new=AsyncMock(return_value=None),
            ),
        ):
            res = _client().get(
                f"/api/v1/geoportal/animals/{animal_id}/darwin-core",
                headers={"Authorization": "Bearer test"},
            )

        assert res.status_code == 200
        assert res.json()["source_status"] == "not_found"
        assert res.json()["taxonomy"] is None


class TestDarwinCoreNoRfidTag:
    def test_location_fields_are_null_when_no_rfid(self):
        animal_id = str(uuid.uuid4())
        animal = _make_animal(animal_id=uuid.UUID(animal_id), rfid_tag=None)

        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animal_by_id",
                new=AsyncMock(return_value=animal),
            ),
            patch(
                "infrastructure.gbif_client.fetch_taxonomy",
                new=AsyncMock(return_value=(GBIF_TAXONOMY_OK, "ok")),
            ),
        ):
            res = _client().get(
                f"/api/v1/geoportal/animals/{animal_id}/darwin-core",
                headers={"Authorization": "Bearer test"},
            )

        assert res.status_code == 200
        obs = res.json()["observation"]
        assert obs["catalog_number"] is None
        assert obs["decimal_latitude"] is None
        assert obs["decimal_longitude"] is None
        assert obs["event_date"] is None
        assert obs["locality"] is None


class TestDarwinCoreNoIotEvents:
    def test_location_fields_are_null_when_no_events_in_mongodb(self):
        animal_id = str(uuid.uuid4())

        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animal_by_id",
                new=AsyncMock(return_value=_make_animal(animal_id=uuid.UUID(animal_id))),
            ),
            patch(
                "infrastructure.gbif_client.fetch_taxonomy",
                new=AsyncMock(return_value=(GBIF_TAXONOMY_OK, "ok")),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_last_rfid_event_for_animal",
                new=AsyncMock(return_value=None),
            ),
        ):
            res = _client().get(
                f"/api/v1/geoportal/animals/{animal_id}/darwin-core",
                headers={"Authorization": "Bearer test"},
            )

        assert res.status_code == 200
        obs = res.json()["observation"]
        assert obs["event_date"] is None
        assert obs["decimal_latitude"] is None
        assert obs["locality"] is None


class TestDarwinCoreFuzzyMatch:
    def test_fuzzy_match_still_returns_taxonomy(self):
        animal_id = str(uuid.uuid4())
        fuzzy_tax = GbifTaxonomyData(
            **{**GBIF_TAXONOMY_OK.__dict__, "gbif_match_type": "FUZZY", "gbif_confidence": 72}
        )

        with (
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_animal_by_id",
                new=AsyncMock(return_value=_make_animal(animal_id=uuid.UUID(animal_id))),
            ),
            patch(
                "infrastructure.gbif_client.fetch_taxonomy",
                new=AsyncMock(return_value=(fuzzy_tax, "fuzzy_match")),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_last_rfid_event_for_animal",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.geoportal.repository.GeoportalRepository.get_station_with_zone",
                new=AsyncMock(return_value=None),
            ),
        ):
            res = _client().get(
                f"/api/v1/geoportal/animals/{animal_id}/darwin-core",
                headers={"Authorization": "Bearer test"},
            )

        assert res.status_code == 200
        body = res.json()
        assert body["source_status"] == "fuzzy_match"
        assert body["taxonomy"] is not None
        assert body["taxonomy"]["kingdom"] == "Animalia"
        assert body["taxonomy"]["gbif_match_type"] == "FUZZY"
