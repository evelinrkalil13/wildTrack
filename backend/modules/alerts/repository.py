from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from infrastructure.mongodb import COLLECTION_ALERTS, get_collection
from shared.enums import AlertType


class AlertRepository:
    @staticmethod
    def _col():
        return get_collection(COLLECTION_ALERTS)

    @staticmethod
    async def find_open_alert(station_id: str, alert_type: AlertType) -> Optional[dict]:
        return await AlertRepository._col().find_one(
            {"station_id": station_id, "alert_type": alert_type.value, "resolved": False}
        )

    @staticmethod
    async def insert_alert(document: dict) -> str:
        result = await AlertRepository._col().insert_one(document)
        return str(result.inserted_id)

    @staticmethod
    async def find_by_alert_id(alert_id: str) -> Optional[dict]:
        return await AlertRepository._col().find_one({"alert_id": alert_id})

    @staticmethod
    async def resolve_by_alert_id(alert_id: str, resolved_at: datetime) -> bool:
        result = await AlertRepository._col().update_one(
            {"alert_id": alert_id},
            {"$set": {"resolved": True, "resolved_at": resolved_at}},
        )
        return result.modified_count > 0

    @staticmethod
    async def resolve_open_alerts(station_id: str, alert_type: AlertType) -> None:
        now = datetime.now(timezone.utc)
        await AlertRepository._col().update_many(
            {"station_id": station_id, "alert_type": alert_type.value, "resolved": False},
            {"$set": {"resolved": True, "resolved_at": now}},
        )

    @staticmethod
    async def list_alerts(
        page: int,
        page_size: int,
        station_id: Optional[str] = None,
        resolved: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        query: dict = {}
        if station_id is not None:
            query["station_id"] = station_id
        if resolved is not None:
            query["resolved"] = resolved

        col = AlertRepository._col()
        skip = (page - 1) * page_size
        total = await col.count_documents(query)
        cursor = col.find(query).sort("created_at", -1).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total
