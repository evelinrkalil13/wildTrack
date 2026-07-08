from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from modules.geoportal.repository import GeoportalRepository
from modules.geoportal.schemas import (
    GeoportalDeviceInfo,
    GeoportalRecentEvent,
    GeoportalStationRead,
    GeoportalTelemetry,
)


def _build_device(device) -> GeoportalDeviceInfo:
    return GeoportalDeviceInfo(
        device_id=str(device.id),
        serial_number=device.serial_number,
        status=device.status,
        last_seen=device.last_seen,
    )


def _build_telemetry(doc: dict) -> Optional[GeoportalTelemetry]:
    ts = doc.get("ingested_at") or doc.get("timestamp")
    if ts is None:
        return None
    if not isinstance(ts, datetime):
        return None
    return GeoportalTelemetry(
        temperature_c=doc.get("temperature_c"),
        humidity_pct=doc.get("humidity_pct"),
        wifi_rssi_dbm=doc.get("wifi_rssi_dbm"),
        firmware_version=doc.get("firmware_version"),
        timestamp=ts,
    )


def _build_event(doc: dict) -> Optional[GeoportalRecentEvent]:
    ts = doc.get("ingested_at")
    event_id = doc.get("event_id", "")
    if ts is None or not isinstance(ts, datetime):
        return None
    return GeoportalRecentEvent(
        event_id=event_id,
        timestamp=ts,
        rfid_tag=doc.get("rfid_tag"),
        consumed_g=doc.get("consumed_g"),
        temperature_c=doc.get("temperature_c"),
        humidity_pct=doc.get("humidity_pct"),
        photos_count=doc.get("photos_count", 0) or 0,
        media_urls=doc.get("media_urls") or [],
    )


class GeoportalService:
    @staticmethod
    async def list_stations(session: AsyncSession) -> list[GeoportalStationRead]:
        station_rows = await GeoportalRepository.list_all_stations_with_zones(session)
        if not station_rows:
            return []

        device_map = await GeoportalRepository.list_assigned_devices_by_station(session)
        telemetry_map = await GeoportalRepository.get_latest_telemetry_by_station()
        events_map = await GeoportalRepository.get_recent_events_by_station()
        alert_map = await GeoportalRepository.get_open_alert_counts_by_station()

        results: list[GeoportalStationRead] = []
        for row in station_rows:
            station_id_str = str(row.station_id)

            device = device_map.get(station_id_str)
            telemetry_doc = telemetry_map.get(station_id_str)
            event_docs = events_map.get(station_id_str, [])
            open_alerts = alert_map.get(station_id_str, 0)

            telemetry = _build_telemetry(telemetry_doc) if telemetry_doc else None
            recent_events = [e for doc in event_docs if (e := _build_event(doc)) is not None]

            results.append(
                GeoportalStationRead(
                    station_id=station_id_str,
                    station_code=row.station_code,
                    station_name=row.station_name,
                    status=row.station_status,
                    latitude=float(row.latitude),
                    longitude=float(row.longitude),
                    zone_id=str(row.zone_id),
                    zone_name=row.zone_name,
                    device=_build_device(device) if device else None,
                    latest_telemetry=telemetry,
                    recent_events=recent_events,
                    open_alerts_count=open_alerts,
                )
            )
        return results
