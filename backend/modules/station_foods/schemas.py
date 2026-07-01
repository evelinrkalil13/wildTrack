from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from shared.pagination import PaginatedResponse


class StationFoodAdd(BaseModel):
    food_id: UUID
    active: bool = True


class StationFoodRead(BaseModel):
    id: UUID
    station_id: UUID
    food_id: UUID
    food_name: str
    food_type: str
    active: bool
    created_at: datetime
    updated_at: datetime


StationFoodListResponse = PaginatedResponse[StationFoodRead]
