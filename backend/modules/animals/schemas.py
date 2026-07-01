from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from shared.enums import AnimalSex
from shared.pagination import PaginatedResponse


class AnimalCreate(BaseModel):
    rfid_tag: Optional[str] = Field(None, min_length=1, max_length=100)
    species: str = Field(..., min_length=2, max_length=255)
    sex: AnimalSex = AnimalSex.unknown
    estimated_age: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class AnimalUpdate(BaseModel):
    rfid_tag: Optional[str] = Field(None, min_length=1, max_length=100)
    species: Optional[str] = Field(None, min_length=2, max_length=255)
    sex: Optional[AnimalSex] = None
    estimated_age: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class AnimalRead(BaseModel):
    id: UUID
    rfid_tag: Optional[str]
    species: str
    sex: AnimalSex
    estimated_age: Optional[str]
    is_identified: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class AnimalStationsRead(BaseModel):
    animal_id: UUID
    rfid_tag: Optional[str]
    stations: list


AnimalListResponse = PaginatedResponse[AnimalRead]
