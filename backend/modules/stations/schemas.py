from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import StationStatus
from shared.pagination import PaginatedResponse


class StationCreate(BaseModel):
    code: str = Field(..., max_length=50, pattern=r"^[A-Z0-9\-]{2,50}$")
    name: str = Field(..., min_length=2, max_length=255)
    zone_id: UUID
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class StationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    status: Optional[StationStatus] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    zone_id: Optional[UUID] = None


class StationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    zone_id: UUID
    latitude: float
    longitude: float
    status: StationStatus
    created_at: datetime
    updated_at: datetime


StationListResponse = PaginatedResponse[StationRead]
