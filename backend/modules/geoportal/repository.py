from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.mongodb import (
    COLLECTION_ALERTS,
    COLLECTION_IOT_EVENTS,
    COLLECTION_TELEMETRY,
    get_collection,
)
from modules.devices.models import Device
from modules.stations.models import Station
from modules.zones.models import Zone


class GeoportalRepository:
    @staticmethod
    async def list_all_stations_with_zones(session: AsyncSession) -> list:
        result = await session.execute(
            select(
                Station.id.label("station_id"),
                Station.code.label("station_code"),
                Station.name.label("station_name"),
                Station.status.label("station_status"),
                Station.latitude,
                Station.longitude,
                Station.zone_id,
                Zone.name.label("zone_name"),
            )
            .join(Zone, Station.zone_id == Zone.id)
            .where(Station.deleted_at.is_(None))
            .order_by(Station.created_at)
        )
        return result.all()

    @staticmethod
    async def list_assigned_devices_by_station(session: AsyncSession) -> dict:
        result = await session.execute(
            select(Device).where(
                Device.station_id.is_not(None),
                Device.deleted_at.is_(None),
            )
        )
        devices = result.scalars().all()
        return {str(d.station_id): d for d in devices}

    @staticmethod
    async def get_latest_telemetry_by_station() -> dict:
        pipeline = [
            {"$match": {"station_id": {"$ne": None}}},
            {"$sort": {"ingested_at": -1}},
            {"$group": {"_id": "$station_id", "doc": {"$first": "$$ROOT"}}},
        ]
        cursor = get_collection(COLLECTION_TELEMETRY).aggregate(pipeline)
        result: dict = {}
        async for doc in cursor:
            result[doc["_id"]] = doc["doc"]
        return result

    @staticmethod
    async def get_recent_events_by_station(limit: int = 3) -> dict:
        pipeline = [
            {"$match": {"station_id": {"$ne": None}}},
            {"$sort": {"ingested_at": -1}},
            {"$group": {"_id": "$station_id", "events": {"$push": "$$ROOT"}}},
            {"$project": {"events": {"$slice": ["$events", limit]}}},
        ]
        cursor = get_collection(COLLECTION_IOT_EVENTS).aggregate(pipeline)
        result: dict = {}
        async for doc in cursor:
            result[doc["_id"]] = doc["events"]
        return result

    @staticmethod
    async def get_open_alert_counts_by_station() -> dict:
        pipeline = [
            {"$match": {"resolved": False, "station_id": {"$ne": None}}},
            {"$group": {"_id": "$station_id", "count": {"$sum": 1}}},
        ]
        cursor = get_collection(COLLECTION_ALERTS).aggregate(pipeline)
        result: dict = {}
        async for doc in cursor:
            result[doc["_id"]] = doc["count"]
        return result
