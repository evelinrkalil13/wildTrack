import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.foods.exceptions import FoodInUseError, FoodNameConflictError, FoodNotFoundError
from modules.foods.schemas import FoodCreate, FoodRead, FoodUpdate
from modules.foods.service import FoodService
from shared.enums import UserRole


def _make_food(**kwargs) -> MagicMock:
    f = MagicMock()
    f.id = kwargs.get("id", uuid.uuid4())
    f.name = kwargs.get("name", "Mixed Seeds")
    f.type = kwargs.get("type", "seeds")
    f.description = kwargs.get("description", None)
    f.deleted_at = None
    now = datetime.now(timezone.utc)
    f.created_at = now
    f.updated_at = now
    return f


def _make_user(role: UserRole = UserRole.researcher) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


@pytest.fixture
def session():
    return AsyncMock()


# ---------------------------------------------------------------------------
# create_food
# ---------------------------------------------------------------------------

class TestCreateFood:
    async def test_creates_food_successfully(self, session):
        food = _make_food(name="Pellets", type="pellets")
        user = _make_user(UserRole.researcher)
        with (
            patch("modules.foods.service.FoodRepository.find_by_name", new=AsyncMock(return_value=None)),
            patch("modules.foods.service.FoodRepository.create", new=AsyncMock(return_value=food)),
        ):
            result = await FoodService.create_food(session, FoodCreate(name="Pellets", type="pellets"), user)
        assert isinstance(result, FoodRead)
        assert result.name == "Pellets"

    async def test_raises_conflict_on_duplicate_name(self, session):
        existing = _make_food(name="Pellets")
        user = _make_user()
        with patch("modules.foods.service.FoodRepository.find_by_name", new=AsyncMock(return_value=existing)):
            with pytest.raises(FoodNameConflictError):
                await FoodService.create_food(session, FoodCreate(name="Pellets", type="seeds"), user)

    async def test_creates_food_with_description(self, session):
        food = _make_food(description="Sunflower and corn mix")
        user = _make_user()
        with (
            patch("modules.foods.service.FoodRepository.find_by_name", new=AsyncMock(return_value=None)),
            patch("modules.foods.service.FoodRepository.create", new=AsyncMock(return_value=food)),
        ):
            result = await FoodService.create_food(
                session,
                FoodCreate(name="Mix", type="seeds", description="Sunflower and corn mix"),
                user,
            )
        assert result.description == "Sunflower and corn mix"


# ---------------------------------------------------------------------------
# get_food
# ---------------------------------------------------------------------------

class TestGetFood:
    async def test_returns_food_read(self, session):
        food = _make_food()
        user = _make_user()
        with patch("modules.foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=food)):
            result = await FoodService.get_food(session, food.id, user)
        assert isinstance(result, FoodRead)
        assert result.id == food.id

    async def test_raises_not_found(self, session):
        user = _make_user()
        with patch("modules.foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(FoodNotFoundError):
                await FoodService.get_food(session, uuid.uuid4(), user)


# ---------------------------------------------------------------------------
# update_food
# ---------------------------------------------------------------------------

class TestUpdateFood:
    async def test_updates_name(self, session):
        food = _make_food(name="Old Name")
        updated = _make_food(name="New Name")
        user = _make_user()
        with (
            patch("modules.foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=food)),
            patch("modules.foods.service.FoodRepository.find_by_name", new=AsyncMock(return_value=None)),
            patch("modules.foods.service.FoodRepository.update", new=AsyncMock(return_value=updated)),
        ):
            result = await FoodService.update_food(session, food.id, FoodUpdate(name="New Name"), user)
        assert result.name == "New Name"

    async def test_raises_conflict_when_new_name_taken(self, session):
        food = _make_food(name="Old Name")
        other = _make_food(name="Taken Name")
        user = _make_user()
        with (
            patch("modules.foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=food)),
            patch("modules.foods.service.FoodRepository.find_by_name", new=AsyncMock(return_value=other)),
        ):
            with pytest.raises(FoodNameConflictError):
                await FoodService.update_food(session, food.id, FoodUpdate(name="Taken Name"), user)

    async def test_same_name_does_not_trigger_conflict_check(self, session):
        food = _make_food(name="Same Name")
        updated = _make_food(name="Same Name")
        user = _make_user()
        with (
            patch("modules.foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=food)),
            patch("modules.foods.service.FoodRepository.update", new=AsyncMock(return_value=updated)),
        ):
            result = await FoodService.update_food(session, food.id, FoodUpdate(name="Same Name"), user)
        assert result.name == "Same Name"

    async def test_raises_not_found(self, session):
        user = _make_user()
        with patch("modules.foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(FoodNotFoundError):
                await FoodService.update_food(session, uuid.uuid4(), FoodUpdate(), user)


# ---------------------------------------------------------------------------
# delete_food
# ---------------------------------------------------------------------------

class TestDeleteFood:
    async def test_deletes_food_when_not_in_use(self, session):
        food = _make_food()
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=food)),
            patch("modules.foods.service.StationFoodRepository.has_active_for_food", new=AsyncMock(return_value=False)),
            patch("modules.foods.service.FoodRepository.soft_delete", new=AsyncMock()),
        ):
            await FoodService.delete_food(session, food.id, admin)

    async def test_raises_food_in_use_when_active_at_station(self, session):
        food = _make_food()
        admin = _make_user(UserRole.admin)
        with (
            patch("modules.foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=food)),
            patch("modules.foods.service.StationFoodRepository.has_active_for_food", new=AsyncMock(return_value=True)),
        ):
            with pytest.raises(FoodInUseError):
                await FoodService.delete_food(session, food.id, admin)

    async def test_raises_not_found(self, session):
        admin = _make_user(UserRole.admin)
        with patch("modules.foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(FoodNotFoundError):
                await FoodService.delete_food(session, uuid.uuid4(), admin)


# ---------------------------------------------------------------------------
# list_foods
# ---------------------------------------------------------------------------

class TestListFoods:
    async def test_returns_paginated_response(self, session):
        foods = [_make_food() for _ in range(5)]
        user = _make_user()
        with patch("modules.foods.service.FoodRepository.list_all", new=AsyncMock(return_value=(foods, 5))):
            result = await FoodService.list_foods(session, 1, 20, user)
        assert result.total == 5
        assert len(result.items) == 5
