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


class FoodStationRead(BaseModel):
    station_id: UUID
    station_code: str
    station_name: str
    active: bool
    created_at: datetime


class FoodStationListResponse(BaseModel):
    total: int
    items: list[FoodStationRead]
