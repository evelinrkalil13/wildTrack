from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from shared.enums import AlertType


class AlertRead(BaseModel):
    alert_id: str
    alert_type: AlertType
    station_id: Optional[str] = None
    device_id: Optional[str] = None
    event_id: Optional[str] = None
    message: str
    resolved: bool
    resolved_at: Optional[datetime] = None
    created_at: datetime


class AlertListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[AlertRead]
