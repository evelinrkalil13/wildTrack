from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

from shared.enums import StationUserRole
from shared.pagination import PaginatedResponse


class MemberAssign(BaseModel):
    user_id: UUID
    role: StationUserRole

    @field_validator("role")
    @classmethod
    def role_must_not_be_owner(cls, v: StationUserRole) -> StationUserRole:
        if v == StationUserRole.owner:
            raise ValueError("Cannot assign the owner role via this endpoint")
        return v


class MemberUpdate(BaseModel):
    role: StationUserRole

    @field_validator("role")
    @classmethod
    def role_must_not_be_owner(cls, v: StationUserRole) -> StationUserRole:
        if v == StationUserRole.owner:
            raise ValueError("Cannot assign the owner role via this endpoint")
        return v


class MemberRead(BaseModel):
    id: UUID
    station_id: UUID
    user_id: UUID
    user_name: str
    user_email: str
    role: StationUserRole
    created_at: datetime


MemberListResponse = PaginatedResponse[MemberRead]
