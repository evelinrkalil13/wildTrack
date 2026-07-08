from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from shared.enums import DeviceStatus, StationStatus


class GeoportalDeviceInfo(BaseModel):
    device_id: str
    serial_number: str
    status: DeviceStatus
    last_seen: Optional[datetime]


class GeoportalTelemetry(BaseModel):
    temperature_c: Optional[float]
    humidity_pct: Optional[float]
    wifi_rssi_dbm: Optional[int]
    firmware_version: Optional[str]
    timestamp: datetime


class GeoportalRecentEvent(BaseModel):
    event_id: str
    timestamp: datetime
    rfid_tag: Optional[str]
    consumed_g: Optional[float]
    temperature_c: Optional[float]
    humidity_pct: Optional[float]
    photos_count: int
    media_urls: list[str] = []


class GeoportalStationRead(BaseModel):
    station_id: str
    station_code: str
    station_name: str
    status: StationStatus
    latitude: float
    longitude: float
    zone_id: str
    zone_name: str
    device: Optional[GeoportalDeviceInfo]
    latest_telemetry: Optional[GeoportalTelemetry]
    recent_events: list[GeoportalRecentEvent]
    open_alerts_count: int
