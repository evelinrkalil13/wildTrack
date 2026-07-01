from datetime import datetime, timezone
from typing import Optional

from modules.alerts.exceptions import AlertNotFoundError
from modules.alerts.repository import AlertRepository
from modules.alerts.schemas import AlertListResponse, AlertRead
from shared.enums import AlertType
from shared.uuid7 import generate_uuid7


def _doc_to_read(doc: dict) -> AlertRead:
    return AlertRead(
        alert_id=doc["alert_id"],
        alert_type=AlertType(doc["alert_type"]),
        station_id=doc.get("station_id"),
        device_id=doc.get("device_id"),
        event_id=doc.get("event_id"),
        message=doc["message"],
        resolved=doc["resolved"],
        resolved_at=doc.get("resolved_at"),
        created_at=doc["created_at"],
    )


class AlertService:
    @staticmethod
    async def raise_alert(
        *,
        alert_type: AlertType,
        station_id: str,
        device_id: Optional[str] = None,
        event_id: Optional[str] = None,
        message: str,
    ) -> None:
        existing = await AlertRepository.find_open_alert(station_id, alert_type)
        if existing is not None:
            return
        now = datetime.now(timezone.utc)
        doc = {
            "alert_id": str(generate_uuid7()),
            "alert_type": alert_type.value,
            "station_id": station_id,
            "device_id": device_id,
            "event_id": event_id,
            "message": message,
            "resolved": False,
            "resolved_at": None,
            "created_at": now,
        }
        await AlertRepository.insert_alert(doc)

    @staticmethod
    async def resolve_open_alerts(station_id: str, alert_type: AlertType) -> None:
        await AlertRepository.resolve_open_alerts(station_id, alert_type)

    @staticmethod
    async def get_alert(alert_id: str) -> AlertRead:
        doc = await AlertRepository.find_by_alert_id(alert_id)
        if doc is None:
            raise AlertNotFoundError()
        return _doc_to_read(doc)

    @staticmethod
    async def resolve_alert(alert_id: str) -> AlertRead:
        doc = await AlertRepository.find_by_alert_id(alert_id)
        if doc is None:
            raise AlertNotFoundError()
        if not doc["resolved"]:
            now = datetime.now(timezone.utc)
            await AlertRepository.resolve_by_alert_id(alert_id, now)
            doc = await AlertRepository.find_by_alert_id(alert_id)
        return _doc_to_read(doc)

    @staticmethod
    async def list_alerts(
        page: int,
        page_size: int,
        station_id: Optional[str] = None,
        resolved: Optional[bool] = None,
    ) -> AlertListResponse:
        items_raw, total = await AlertRepository.list_alerts(page, page_size, station_id, resolved)
        items = [_doc_to_read(d) for d in items_raw]
        pages = max(1, (total + page_size - 1) // page_size)
        return AlertListResponse(
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            items=items,
        )
