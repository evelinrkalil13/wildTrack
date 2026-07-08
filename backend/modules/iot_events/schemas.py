from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RfidPayload(BaseModel):
    detected: bool
    tag: Optional[str] = None
    read_quality: Optional[str] = None


class SensorsPayload(BaseModel):
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    initial_weight_g: Optional[float] = None
    final_weight_g: Optional[float] = None
    consumed_g: Optional[float] = None


class MediaPayload(BaseModel):
    captured: int = 0
    urls: list[str] = Field(default_factory=list)


class DeviceStatusPayload(BaseModel):
    wifi_rssi_dbm: Optional[int] = None
    firmware_version: Optional[str] = None
    battery_pct: Optional[float] = None


class FeedingEventPayload(BaseModel):
    event_id: str
    event_type: str
    device_id: str
    timestamp: datetime
    rfid: RfidPayload
    sensors: SensorsPayload
    media: MediaPayload = Field(default_factory=MediaPayload)
    device_status: DeviceStatusPayload = Field(default_factory=DeviceStatusPayload)


class TelemetryPayload(BaseModel):
    device_id: str
    timestamp: datetime
    sensors: Optional[SensorsPayload] = None
    device_status: Optional[DeviceStatusPayload] = None


class StatusPayload(BaseModel):
    # device_id and timestamp are optional: the ESP32 LWT message omits them.
    # device_id is always taken from the MQTT topic path instead.
    device_id: Optional[str] = None
    status: str
    timestamp: Optional[datetime] = None
