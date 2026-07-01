from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from modules.stations.exceptions import StationNotFoundError
from modules.stations.repository import StationRepository
from modules.user_stations.exceptions import (
    AlreadyMemberError,
    CannotAssignOwnerError,
    CannotChangeOwnerRoleError,
    CannotRemoveOwnerError,
    MemberAccessDeniedError,
    MemberNotFoundError,
)
from modules.user_stations.models import UserStation
from modules.user_stations.repository import UserStationRepository
from modules.user_stations.schemas import (
    MemberAssign,
    MemberListResponse,
    MemberRead,
    MemberUpdate,
)
from modules.users.repository import UserRepository
from shared.base_exception import NotFoundError
from shared.enums import StationUserRole, UserRole
from shared.pagination import make_paginated_response, paginate
from shared.uuid7 import generate_uuid7


def _is_admin(user) -> bool:
    role_val = user.role.value if hasattr(user.role, "value") else user.role
    return role_val == UserRole.admin.value


def _to_read(us: UserStation, user_name: str, user_email: str) -> MemberRead:
    return MemberRead(
        id=us.id,
        station_id=us.station_id,
        user_id=us.user_id,
        user_name=user_name,
        user_email=user_email,
        role=us.role,
        created_at=us.created_at,
    )


async def _require_station_owner_or_admin(session, station_id: UUID, current_user) -> None:
    station = await StationRepository.find_by_id(session, station_id)
    if station is None:
        raise StationNotFoundError()
    if not _is_admin(current_user):
        role = await UserStationRepository.get_user_role_in_station(
            session, current_user.id, station_id
        )
        if role != StationUserRole.owner:
            raise MemberAccessDeniedError()


async def _require_station_member_or_admin(session, station_id: UUID, current_user) -> None:
    station = await StationRepository.find_by_id(session, station_id)
    if station is None:
        raise StationNotFoundError()
    if not _is_admin(current_user):
        has_access = await UserStationRepository.user_has_access(
            session, current_user.id, station_id
        )
        if not has_access:
            raise MemberAccessDeniedError()


class MemberService:
    @staticmethod
    async def assign_member(
        session: AsyncSession, station_id: UUID, data: MemberAssign, current_user
    ) -> MemberRead:
        await _require_station_owner_or_admin(session, station_id, current_user)

        if data.role == StationUserRole.owner:
            raise CannotAssignOwnerError()

        target_user = await UserRepository.find_by_id(session, data.user_id)
        if target_user is None:
            raise NotFoundError()

        existing = await UserStationRepository.find_by_user_and_station(
            session, data.user_id, station_id
        )
        if existing is not None:
            raise AlreadyMemberError()

        us = UserStation(
            id=generate_uuid7(),
            user_id=data.user_id,
            station_id=station_id,
            role=data.role,
        )
        us = await UserStationRepository.create(session, us)
        return _to_read(us, target_user.name, target_user.email)

    @staticmethod
    async def list_members(
        session: AsyncSession,
        station_id: UUID,
        page: int,
        page_size: int,
        current_user,
    ) -> MemberListResponse:
        await _require_station_member_or_admin(session, station_id, current_user)

        offset, limit = paginate(page, page_size)
        rows, total = await UserStationRepository.list_for_station_with_users(
            session, station_id, offset, limit
        )
        items = [_to_read(us, user_name, user_email) for us, user_name, user_email in rows]
        return MemberListResponse(**make_paginated_response(items, total, page, limit))

    @staticmethod
    async def update_member_role(
        session: AsyncSession,
        station_id: UUID,
        us_id: UUID,
        data: MemberUpdate,
        current_user,
    ) -> MemberRead:
        await _require_station_owner_or_admin(session, station_id, current_user)

        us = await UserStationRepository.find_by_id_in_station(session, us_id, station_id)
        if us is None:
            raise MemberNotFoundError()

        if us.role == StationUserRole.owner:
            raise CannotChangeOwnerRoleError()

        if data.role == StationUserRole.owner:
            raise CannotAssignOwnerError()

        target_user = await UserRepository.find_by_id(session, us.user_id)
        us.role = data.role
        us = await UserStationRepository.update(session, us)
        return _to_read(us, target_user.name, target_user.email)

    @staticmethod
    async def remove_member(
        session: AsyncSession,
        station_id: UUID,
        us_id: UUID,
        current_user,
    ) -> None:
        await _require_station_owner_or_admin(session, station_id, current_user)

        us = await UserStationRepository.find_by_id_in_station(session, us_id, station_id)
        if us is None:
            raise MemberNotFoundError()

        if us.role == StationUserRole.owner:
            raise CannotRemoveOwnerError()

        await UserStationRepository.soft_delete_one(session, us)
