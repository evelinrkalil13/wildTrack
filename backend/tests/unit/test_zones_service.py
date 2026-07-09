import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.zones.exceptions import (
    ZoneHasActiveStationsError,
    ZoneNameConflictError,
    ZoneNotFoundError,
)
from modules.zones.schemas import ZoneCreate, ZoneRead, ZoneUpdate
from modules.zones.service import ZoneService


def _make_zone(**kwargs) -> MagicMock:
    zone = MagicMock()
    zone.id = uuid.uuid4()
    zone.name = kwargs.get("name", "Test Zone")
    zone.municipality = kwargs.get("municipality", "Mun")
    zone.city = kwargs.get("city", "City")
    zone.country = kwargs.get("country", "CO")
    zone.altitude = kwargs.get("altitude", 1200.0)
    zone.latitude = kwargs.get("latitude", 4.5)
    zone.longitude = kwargs.get("longitude", -74.1)
    zone.color = kwargs.get("color", "#52b788")
    zone.geom = None
    zone.deleted_at = None
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    zone.created_at = now
    zone.updated_at = now
    return zone


@pytest.fixture
def session():
    return AsyncMock()


class TestCreateZone:
    async def test_creates_zone_successfully(self, session):
        zone_obj = _make_zone()
        with (
            patch(
                "modules.zones.service.ZoneRepository.find_by_name_and_country",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.zones.service.ZoneRepository.create",
                new=AsyncMock(return_value=zone_obj),
            ),
            patch("modules.zones.service.ZoneRepository.build_geom", return_value=None),
        ):
            data = ZoneCreate(
                name="Test Zone",
                city="City",
                country="CO",
                latitude=4.5,
                longitude=-74.1,
            )
            result = await ZoneService.create_zone(session, data)
        assert isinstance(result, ZoneRead)
        assert result.name == zone_obj.name

    async def test_raises_conflict_when_name_country_exists(self, session):
        with patch(
            "modules.zones.service.ZoneRepository.find_by_name_and_country",
            new=AsyncMock(return_value=_make_zone()),
        ):
            data = ZoneCreate(
                name="Test Zone", city="City", country="CO", latitude=4.5, longitude=-74.1
            )
            with pytest.raises(ZoneNameConflictError):
                await ZoneService.create_zone(session, data)


class TestGetZone:
    async def test_returns_zone_when_found(self, session):
        zone_obj = _make_zone()
        with patch(
            "modules.zones.service.ZoneRepository.find_by_id",
            new=AsyncMock(return_value=zone_obj),
        ):
            result = await ZoneService.get_zone(session, zone_obj.id)
        assert isinstance(result, ZoneRead)

    async def test_raises_not_found(self, session):
        with patch(
            "modules.zones.service.ZoneRepository.find_by_id",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(ZoneNotFoundError):
                await ZoneService.get_zone(session, uuid.uuid4())


class TestListZones:
    async def test_returns_paginated_response(self, session):
        zones = [_make_zone() for _ in range(3)]
        with patch(
            "modules.zones.service.ZoneRepository.list_all",
            new=AsyncMock(return_value=(zones, 3)),
        ) as mock_list:
            result = await ZoneService.list_zones(session, page=1, page_size=20)
            mock_list.assert_called_once_with(session, 0, 20, country=None)
        assert result.total == 3
        assert len(result.items) == 3
        assert result.page == 1

    async def test_empty_list(self, session):
        with patch(
            "modules.zones.service.ZoneRepository.list_all",
            new=AsyncMock(return_value=([], 0)),
        ):
            result = await ZoneService.list_zones(session, page=1, page_size=20)
        assert result.total == 0
        assert result.items == []
        assert result.pages == 0

    async def test_passes_country_filter_to_repository(self, session):
        zones = [_make_zone(country="CO")]
        with patch(
            "modules.zones.service.ZoneRepository.list_all",
            new=AsyncMock(return_value=(zones, 1)),
        ) as mock_list:
            result = await ZoneService.list_zones(session, page=1, page_size=20, country="CO")
            mock_list.assert_called_once_with(session, 0, 20, country="CO")
        assert result.total == 1


class TestUpdateZone:
    async def test_updates_zone_successfully(self, session):
        zone_obj = _make_zone()
        with (
            patch(
                "modules.zones.service.ZoneRepository.find_by_id",
                new=AsyncMock(return_value=zone_obj),
            ),
            patch(
                "modules.zones.service.ZoneRepository.find_by_name_and_country",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.zones.service.ZoneRepository.update",
                new=AsyncMock(return_value=zone_obj),
            ),
            patch("modules.zones.service.ZoneRepository.build_geom", return_value=None),
        ):
            data = ZoneUpdate(name="New Name")
            result = await ZoneService.update_zone(session, zone_obj.id, data)
        assert isinstance(result, ZoneRead)

    async def test_raises_not_found_on_update(self, session):
        with patch(
            "modules.zones.service.ZoneRepository.find_by_id",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(ZoneNotFoundError):
                await ZoneService.update_zone(session, uuid.uuid4(), ZoneUpdate(name="Xy"))

    async def test_raises_conflict_on_name_update(self, session):
        zone_obj = _make_zone()
        conflict_zone = _make_zone(name="Other Zone")
        with (
            patch(
                "modules.zones.service.ZoneRepository.find_by_id",
                new=AsyncMock(return_value=zone_obj),
            ),
            patch(
                "modules.zones.service.ZoneRepository.find_by_name_and_country",
                new=AsyncMock(return_value=conflict_zone),
            ),
        ):
            with pytest.raises(ZoneNameConflictError):
                await ZoneService.update_zone(session, zone_obj.id, ZoneUpdate(name="Other Zone"))


class TestDeleteZone:
    async def test_deletes_zone_successfully(self, session):
        zone_obj = _make_zone()
        with (
            patch(
                "modules.zones.service.ZoneRepository.find_by_id",
                new=AsyncMock(return_value=zone_obj),
            ),
            patch(
                "modules.zones.service.ZoneRepository.has_active_stations",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "modules.zones.service.ZoneRepository.soft_delete",
                new=AsyncMock(return_value=None),
            ),
        ):
            await ZoneService.delete_zone(session, zone_obj.id)

    async def test_raises_not_found_on_delete(self, session):
        with patch(
            "modules.zones.service.ZoneRepository.find_by_id",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(ZoneNotFoundError):
                await ZoneService.delete_zone(session, uuid.uuid4())

    async def test_raises_has_active_stations(self, session):
        zone_obj = _make_zone()
        with (
            patch(
                "modules.zones.service.ZoneRepository.find_by_id",
                new=AsyncMock(return_value=zone_obj),
            ),
            patch(
                "modules.zones.service.ZoneRepository.has_active_stations",
                new=AsyncMock(return_value=True),
            ),
        ):
            with pytest.raises(ZoneHasActiveStationsError):
                await ZoneService.delete_zone(session, zone_obj.id)
