from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import DeviceStatus
from shared.pagination import PaginatedResponse


class DeviceCreate(BaseModel):
    serial_number: str = Field(..., min_length=3, max_length=100)
    name: Optional[str] = Field(None, max_length=255)
    mac_address: Optional[str] = Field(
        None,
        pattern=r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$",
    )


class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)


class DeviceAssign(BaseModel):
    station_id: UUID


class DeviceRead(BaseModel):
    id: UUID
    serial_number: str
    name: Optional[str]
    mac_address: Optional[str]
    station_id: Optional[UUID]
    station_code: Optional[str]
    status: DeviceStatus
    firmware_version: Optional[str]
    last_seen: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class DeviceAssignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    station_id: Optional[UUID]
    status: DeviceStatus
    updated_at: datetime


DeviceListResponse = PaginatedResponse[DeviceRead]
