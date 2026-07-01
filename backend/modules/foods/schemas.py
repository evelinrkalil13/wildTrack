from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from shared.pagination import PaginatedResponse


class FoodCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    type: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class FoodUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    type: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class FoodRead(BaseModel):
    id: UUID
    name: str
    type: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


FoodListResponse = PaginatedResponse[FoodRead]
