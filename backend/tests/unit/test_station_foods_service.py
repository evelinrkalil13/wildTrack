import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.foods.exceptions import FoodNotFoundError
from modules.station_foods.exceptions import (
    CannotRemoveActiveFoodError,
    FoodAlreadyAssociatedError,
    StationFoodAccessDeniedError,
    StationFoodNotFoundError,
)
from modules.station_foods.schemas import StationFoodAdd, StationFoodRead
from modules.station_foods.service import StationFoodService
from modules.stations.exceptions import StationNotFoundError
from shared.enums import StationUserRole, UserRole


def _make_station() -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.deleted_at = None
    return s


def _make_food(**kwargs) -> MagicMock:
    f = MagicMock()
    f.id = kwargs.get("id", uuid.uuid4())
    f.name = kwargs.get("name", "Mixed Seeds")
    f.type = kwargs.get("type", "seeds")
    return f


def _make_sf(**kwargs) -> MagicMock:
    sf = MagicMock()
    sf.id = kwargs.get("id", uuid.uuid4())
    sf.station_id = kwargs.get("station_id", uuid.uuid4())
    sf.food_id = kwargs.get("food_id", uuid.uuid4())
    sf.active = kwargs.get("active", True)
    now = datetime.now(timezone.utc)
    sf.created_at = now
    sf.updated_at = now
    return sf


def _make_user(role: UserRole = UserRole.researcher) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


def _make_admin() -> MagicMock:
    return _make_user(UserRole.admin)


@pytest.fixture
def session():
    return AsyncMock()


# ---------------------------------------------------------------------------
# add_food
# ---------------------------------------------------------------------------

class TestAddFood:
    async def test_adds_food_as_active(self, session):
        station = _make_station()
        food = _make_food()
        sf = _make_sf(station_id=station.id, food_id=food.id, active=True)
        admin = _make_admin()
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.station_foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=food)),
            patch("modules.station_foods.service.StationFoodRepository.find_by_station_and_food", new=AsyncMock(return_value=None)),
            patch("modules.station_foods.service.StationFoodRepository.find_active_for_station", new=AsyncMock(return_value=None)),
            patch("modules.station_foods.service.StationFoodRepository.create", new=AsyncMock(return_value=sf)),
        ):
            result = await StationFoodService.add_food(
                session, station.id, StationFoodAdd(food_id=food.id, active=True), admin
            )
        assert isinstance(result, StationFoodRead)
        assert result.active is True

    async def test_adds_food_deactivates_current_active(self, session):
        station = _make_station()
        food = _make_food()
        current_active = _make_sf(active=True)
        new_sf = _make_sf(station_id=station.id, food_id=food.id, active=True)
        admin = _make_admin()
        mock_deactivate = AsyncMock()
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.station_foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=food)),
            patch("modules.station_foods.service.StationFoodRepository.find_by_station_and_food", new=AsyncMock(return_value=None)),
            patch("modules.station_foods.service.StationFoodRepository.find_active_for_station", new=AsyncMock(return_value=current_active)),
            patch("modules.station_foods.service.StationFoodRepository.deactivate", new=mock_deactivate),
            patch("modules.station_foods.service.StationFoodRepository.create", new=AsyncMock(return_value=new_sf)),
        ):
            await StationFoodService.add_food(
                session, station.id, StationFoodAdd(food_id=food.id, active=True), admin
            )
        mock_deactivate.assert_awaited_once_with(session, current_active)

    async def test_adds_food_as_inactive_does_not_deactivate_current(self, session):
        station = _make_station()
        food = _make_food()
        current_active = _make_sf(active=True)
        new_sf = _make_sf(active=False)
        admin = _make_admin()
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.station_foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=food)),
            patch("modules.station_foods.service.StationFoodRepository.find_by_station_and_food", new=AsyncMock(return_value=None)),
            patch("modules.station_foods.service.StationFoodRepository.create", new=AsyncMock(return_value=new_sf)),
        ):
            await StationFoodService.add_food(
                session, station.id, StationFoodAdd(food_id=food.id, active=False), admin
            )
        assert current_active.active is True

    async def test_raises_station_not_found(self, session):
        admin = _make_admin()
        with patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(StationNotFoundError):
                await StationFoodService.add_food(
                    session, uuid.uuid4(), StationFoodAdd(food_id=uuid.uuid4()), admin
                )

    async def test_raises_food_not_found(self, session):
        station = _make_station()
        admin = _make_admin()
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.station_foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=None)),
        ):
            with pytest.raises(FoodNotFoundError):
                await StationFoodService.add_food(
                    session, station.id, StationFoodAdd(food_id=uuid.uuid4()), admin
                )

    async def test_raises_food_already_associated(self, session):
        station = _make_station()
        food = _make_food()
        existing_sf = _make_sf()
        admin = _make_admin()
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.station_foods.service.FoodRepository.find_by_id", new=AsyncMock(return_value=food)),
            patch("modules.station_foods.service.StationFoodRepository.find_by_station_and_food", new=AsyncMock(return_value=existing_sf)),
        ):
            with pytest.raises(FoodAlreadyAssociatedError):
                await StationFoodService.add_food(
                    session, station.id, StationFoodAdd(food_id=food.id), admin
                )

    async def test_non_owner_non_admin_raises_forbidden(self, session):
        station = _make_station()
        user = _make_user(UserRole.researcher)
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.researcher)),
        ):
            with pytest.raises(StationFoodAccessDeniedError):
                await StationFoodService.add_food(
                    session, station.id, StationFoodAdd(food_id=uuid.uuid4()), user
                )


# ---------------------------------------------------------------------------
# activate_station_food
# ---------------------------------------------------------------------------

class TestActivateStationFood:
    async def test_activates_food_and_deactivates_current(self, session):
        station = _make_station()
        current = _make_sf(active=True)
        target_sf = _make_sf(active=False)
        target_after = _make_sf(active=True)
        admin = _make_admin()
        mock_deactivate = AsyncMock()
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.station_foods.service.StationFoodRepository.find_by_id_in_station_with_food", new=AsyncMock(return_value=(target_sf, "Pellets", "pellets"))),
            patch("modules.station_foods.service.StationFoodRepository.find_active_for_station", new=AsyncMock(return_value=current)),
            patch("modules.station_foods.service.StationFoodRepository.deactivate", new=mock_deactivate),
            patch("modules.station_foods.service.StationFoodRepository.update", new=AsyncMock(return_value=target_after)),
        ):
            result = await StationFoodService.activate_station_food(
                session, station.id, target_sf.id, admin
            )
        mock_deactivate.assert_awaited_once_with(session, current)
        assert result.active is True

    async def test_activates_already_active_food_with_no_other_current(self, session):
        station = _make_station()
        sf = _make_sf(active=True)
        sf_after = _make_sf(active=True)
        admin = _make_admin()
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.station_foods.service.StationFoodRepository.find_by_id_in_station_with_food", new=AsyncMock(return_value=(sf, "Seeds", "seeds"))),
            patch("modules.station_foods.service.StationFoodRepository.find_active_for_station", new=AsyncMock(return_value=sf)),
            patch("modules.station_foods.service.StationFoodRepository.update", new=AsyncMock(return_value=sf_after)),
        ):
            result = await StationFoodService.activate_station_food(
                session, station.id, sf.id, admin
            )
        assert result.active is True

    async def test_raises_not_found(self, session):
        station = _make_station()
        admin = _make_admin()
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.station_foods.service.StationFoodRepository.find_by_id_in_station_with_food", new=AsyncMock(return_value=None)),
        ):
            with pytest.raises(StationFoodNotFoundError):
                await StationFoodService.activate_station_food(session, station.id, uuid.uuid4(), admin)


# ---------------------------------------------------------------------------
# deactivate_station_food
# ---------------------------------------------------------------------------

class TestDeactivateStationFood:
    async def test_deactivates_food(self, session):
        station = _make_station()
        sf = _make_sf(active=True)
        sf_after = _make_sf(active=False)
        admin = _make_admin()
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.station_foods.service.StationFoodRepository.find_by_id_in_station_with_food", new=AsyncMock(return_value=(sf, "Seeds", "seeds"))),
            patch("modules.station_foods.service.StationFoodRepository.update", new=AsyncMock(return_value=sf_after)),
        ):
            result = await StationFoodService.deactivate_station_food(session, station.id, sf.id, admin)
        assert result.active is False

    async def test_raises_not_found(self, session):
        station = _make_station()
        admin = _make_admin()
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.station_foods.service.StationFoodRepository.find_by_id_in_station_with_food", new=AsyncMock(return_value=None)),
        ):
            with pytest.raises(StationFoodNotFoundError):
                await StationFoodService.deactivate_station_food(session, station.id, uuid.uuid4(), admin)


# ---------------------------------------------------------------------------
# remove_station_food
# ---------------------------------------------------------------------------

class TestRemoveStationFood:
    async def test_removes_inactive_food(self, session):
        station = _make_station()
        sf = _make_sf(active=False)
        admin = _make_admin()
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.station_foods.service.StationFoodRepository.find_by_id_in_station", new=AsyncMock(return_value=sf)),
            patch("modules.station_foods.service.StationFoodRepository.hard_delete", new=AsyncMock()),
        ):
            await StationFoodService.remove_station_food(session, station.id, sf.id, admin)

    async def test_raises_cannot_remove_active(self, session):
        station = _make_station()
        sf = _make_sf(active=True)
        admin = _make_admin()
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.station_foods.service.StationFoodRepository.find_by_id_in_station", new=AsyncMock(return_value=sf)),
        ):
            with pytest.raises(CannotRemoveActiveFoodError):
                await StationFoodService.remove_station_food(session, station.id, sf.id, admin)

    async def test_raises_not_found(self, session):
        station = _make_station()
        admin = _make_admin()
        with (
            patch("modules.station_foods.service.StationRepository.find_by_id", new=AsyncMock(return_value=station)),
            patch("modules.station_foods.service.UserStationRepository.get_user_role_in_station", new=AsyncMock(return_value=StationUserRole.owner)),
            patch("modules.station_foods.service.StationFoodRepository.find_by_id_in_station", new=AsyncMock(return_value=None)),
        ):
            with pytest.raises(StationFoodNotFoundError):
                await StationFoodService.remove_station_food(session, station.id, uuid.uuid4(), admin)
