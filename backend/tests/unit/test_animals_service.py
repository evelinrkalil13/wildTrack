import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.animals.exceptions import AnimalNotFoundError, RfidTagConflictError
from modules.animals.schemas import AnimalCreate, AnimalRead, AnimalStationsRead, AnimalUpdate
from modules.animals.service import AnimalService
from shared.enums import AnimalSex, UserRole


def _make_animal(**kwargs) -> MagicMock:
    a = MagicMock()
    a.id = kwargs.get("id", uuid.uuid4())
    a.rfid_tag = kwargs.get("rfid_tag", None)
    a.species = kwargs.get("species", "Tremarctos ornatus")
    a.sex = kwargs.get("sex", AnimalSex.unknown)
    a.estimated_age = kwargs.get("estimated_age", None)
    a.is_identified = kwargs.get("is_identified", False)
    a.notes = kwargs.get("notes", None)
    a.deleted_at = None
    now = datetime.now(timezone.utc)
    a.created_at = now
    a.updated_at = now
    return a


def _make_user(role: UserRole = UserRole.researcher) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


@pytest.fixture
def session():
    return AsyncMock()


# ---------------------------------------------------------------------------
# create_animal
# ---------------------------------------------------------------------------

class TestCreateAnimal:
    async def test_creates_animal_without_rfid(self, session):
        animal = _make_animal(is_identified=False)
        user = _make_user()
        with (
            patch("modules.animals.service.AnimalRepository.find_by_rfid", new=AsyncMock(return_value=None)),
            patch("modules.animals.service.AnimalRepository.create", new=AsyncMock(return_value=animal)),
        ):
            result = await AnimalService.create_animal(
                session,
                AnimalCreate(species="Tremarctos ornatus"),
                user,
            )
        assert isinstance(result, AnimalRead)
        assert result.is_identified is False
        assert result.rfid_tag is None

    async def test_creates_animal_with_rfid_sets_is_identified(self, session):
        animal = _make_animal(rfid_tag="RFID-001", is_identified=True)
        user = _make_user()
        with (
            patch("modules.animals.service.AnimalRepository.find_by_rfid", new=AsyncMock(return_value=None)),
            patch("modules.animals.service.AnimalRepository.create", new=AsyncMock(return_value=animal)),
        ):
            result = await AnimalService.create_animal(
                session,
                AnimalCreate(species="Puma concolor", rfid_tag="RFID-001"),
                user,
            )
        assert result.is_identified is True
        assert result.rfid_tag == "RFID-001"

    async def test_raises_conflict_on_duplicate_rfid(self, session):
        existing = _make_animal(rfid_tag="RFID-001")
        user = _make_user()
        with patch("modules.animals.service.AnimalRepository.find_by_rfid", new=AsyncMock(return_value=existing)):
            with pytest.raises(RfidTagConflictError):
                await AnimalService.create_animal(
                    session,
                    AnimalCreate(species="Puma concolor", rfid_tag="RFID-001"),
                    user,
                )

    async def test_skips_rfid_check_when_no_rfid(self, session):
        animal = _make_animal()
        user = _make_user()
        with patch("modules.animals.service.AnimalRepository.create", new=AsyncMock(return_value=animal)):
            result = await AnimalService.create_animal(
                session,
                AnimalCreate(species="Odocoileus virginianus"),
                user,
            )
        assert result.is_identified is False

    async def test_creates_animal_with_sex_and_estimated_age(self, session):
        animal = _make_animal(sex=AnimalSex.female, estimated_age="adult (~4-6 years)")
        user = _make_user()
        with (
            patch("modules.animals.service.AnimalRepository.find_by_rfid", new=AsyncMock(return_value=None)),
            patch("modules.animals.service.AnimalRepository.create", new=AsyncMock(return_value=animal)),
        ):
            result = await AnimalService.create_animal(
                session,
                AnimalCreate(species="Tremarctos ornatus", sex=AnimalSex.female, estimated_age="adult (~4-6 years)"),
                user,
            )
        assert result.sex == AnimalSex.female
        assert result.estimated_age == "adult (~4-6 years)"


# ---------------------------------------------------------------------------
# get_animal
# ---------------------------------------------------------------------------

class TestGetAnimal:
    async def test_returns_animal_read(self, session):
        animal = _make_animal()
        user = _make_user()
        with patch("modules.animals.service.AnimalRepository.find_by_id", new=AsyncMock(return_value=animal)):
            result = await AnimalService.get_animal(session, animal.id, user)
        assert isinstance(result, AnimalRead)
        assert result.id == animal.id

    async def test_raises_not_found(self, session):
        user = _make_user()
        with patch("modules.animals.service.AnimalRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(AnimalNotFoundError):
                await AnimalService.get_animal(session, uuid.uuid4(), user)


# ---------------------------------------------------------------------------
# update_animal
# ---------------------------------------------------------------------------

class TestUpdateAnimal:
    async def test_updates_species(self, session):
        animal = _make_animal(species="Old species")
        updated = _make_animal(species="New species")
        user = _make_user()
        with (
            patch("modules.animals.service.AnimalRepository.find_by_id", new=AsyncMock(return_value=animal)),
            patch("modules.animals.service.AnimalRepository.update", new=AsyncMock(return_value=updated)),
        ):
            result = await AnimalService.update_animal(
                session, animal.id, AnimalUpdate(species="New species"), user
            )
        assert result.species == "New species"

    async def test_setting_rfid_tag_sets_is_identified_true(self, session):
        animal = _make_animal(rfid_tag=None, is_identified=False)
        after = _make_animal(rfid_tag="RFID-NEW", is_identified=True)
        user = _make_user()
        with (
            patch("modules.animals.service.AnimalRepository.find_by_id", new=AsyncMock(return_value=animal)),
            patch("modules.animals.service.AnimalRepository.find_by_rfid", new=AsyncMock(return_value=None)),
            patch("modules.animals.service.AnimalRepository.update", new=AsyncMock(return_value=after)),
        ):
            result = await AnimalService.update_animal(
                session, animal.id, AnimalUpdate(rfid_tag="RFID-NEW"), user
            )
        assert result.is_identified is True

    async def test_clearing_rfid_tag_sets_is_identified_false(self, session):
        animal = _make_animal(rfid_tag="RFID-OLD", is_identified=True)
        after = _make_animal(rfid_tag=None, is_identified=False)
        user = _make_user()

        # Patch model_dump to return rfid_tag: None explicitly
        update_data = AnimalUpdate.model_construct()
        update_data.__pydantic_fields_set__ = {"rfid_tag"}

        with (
            patch("modules.animals.service.AnimalRepository.find_by_id", new=AsyncMock(return_value=animal)),
            patch("modules.animals.service.AnimalRepository.find_by_rfid", new=AsyncMock(return_value=None)),
            patch("modules.animals.service.AnimalRepository.update", new=AsyncMock(return_value=after)),
        ):
            result = await AnimalService.update_animal(
                session, animal.id, AnimalUpdate(rfid_tag=None), user
            )
        assert result.is_identified is False

    async def test_update_rfid_conflict_raises(self, session):
        animal = _make_animal(rfid_tag="RFID-OLD")
        other = _make_animal(rfid_tag="RFID-TAKEN")
        user = _make_user()
        with (
            patch("modules.animals.service.AnimalRepository.find_by_id", new=AsyncMock(return_value=animal)),
            patch("modules.animals.service.AnimalRepository.find_by_rfid", new=AsyncMock(return_value=other)),
        ):
            with pytest.raises(RfidTagConflictError):
                await AnimalService.update_animal(
                    session, animal.id, AnimalUpdate(rfid_tag="RFID-TAKEN"), user
                )

    async def test_update_raises_not_found(self, session):
        user = _make_user()
        with patch("modules.animals.service.AnimalRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(AnimalNotFoundError):
                await AnimalService.update_animal(session, uuid.uuid4(), AnimalUpdate(), user)

    async def test_same_rfid_does_not_trigger_conflict_check(self, session):
        same_id = uuid.uuid4()
        animal = _make_animal(id=same_id, rfid_tag="RFID-SAME")
        after = _make_animal(id=same_id, rfid_tag="RFID-SAME")
        user = _make_user()
        with (
            patch("modules.animals.service.AnimalRepository.find_by_id", new=AsyncMock(return_value=animal)),
            patch("modules.animals.service.AnimalRepository.update", new=AsyncMock(return_value=after)),
        ):
            result = await AnimalService.update_animal(
                session, animal.id, AnimalUpdate(rfid_tag="RFID-SAME"), user
            )
        assert result.rfid_tag == "RFID-SAME"


# ---------------------------------------------------------------------------
# delete_animal
# ---------------------------------------------------------------------------

class TestDeleteAnimal:
    async def test_admin_can_delete(self, session):
        animal = _make_animal()
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.animals.service.AnimalRepository.find_by_id", new=AsyncMock(return_value=animal)),
            patch("modules.animals.service.AnimalRepository.soft_delete", new=AsyncMock()),
        ):
            await AnimalService.delete_animal(session, animal.id, admin)

    async def test_delete_raises_not_found(self, session):
        admin = _make_user(UserRole.admin)
        with patch("modules.animals.service.AnimalRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(AnimalNotFoundError):
                await AnimalService.delete_animal(session, uuid.uuid4(), admin)


# ---------------------------------------------------------------------------
# get_animal_stations (stub)
# ---------------------------------------------------------------------------

class TestGetAnimalStations:
    async def test_returns_empty_stations_list(self, session):
        animal = _make_animal(rfid_tag="RFID-001")
        user = _make_user()
        with patch("modules.animals.service.AnimalRepository.find_by_id", new=AsyncMock(return_value=animal)):
            result = await AnimalService.get_animal_stations(session, animal.id, user)
        assert isinstance(result, AnimalStationsRead)
        assert result.stations == []
        assert result.rfid_tag == "RFID-001"

    async def test_raises_not_found_for_unknown_animal(self, session):
        user = _make_user()
        with patch("modules.animals.service.AnimalRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(AnimalNotFoundError):
                await AnimalService.get_animal_stations(session, uuid.uuid4(), user)


# ---------------------------------------------------------------------------
# list_animals
# ---------------------------------------------------------------------------

class TestListAnimals:
    async def test_returns_paginated_response(self, session):
        animals = [_make_animal() for _ in range(3)]
        user = _make_user()
        with patch("modules.animals.service.AnimalRepository.list_all", new=AsyncMock(return_value=(animals, 3))):
            result = await AnimalService.list_animals(session, 1, 20, user)
        assert result.total == 3
        assert len(result.items) == 3
