from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.pagination import PaginatedResponse


class ZoneCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    municipality: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., max_length=255)
    country: str = Field(..., max_length=100)
    altitude: Optional[float] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters after trim")
        return v


class ZoneUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    municipality: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=255)
    country: Optional[str] = Field(None, max_length=100)
    altitude: Optional[float] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) < 2:
                raise ValueError("Name must be at least 2 characters after trim")
        return v


class ZoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    municipality: Optional[str]
    city: str
    country: str
    altitude: Optional[float]
    latitude: float
    longitude: float
    created_at: datetime
    updated_at: datetime


ZoneListResponse = PaginatedResponse[ZoneRead]
