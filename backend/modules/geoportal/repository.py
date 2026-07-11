from datetime import datetime
from typing import Optional
from uuid import UUID

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
                Zone.color.label("zone_color"),
            )
            .join(Zone, Station.zone_id == Zone.id)
            .where(Station.deleted_at.is_(None))
            .order_by(Station.created_at)
        )
        return result.all()

    @staticmethod
    async def get_station_with_zone_by_id(
        session: AsyncSession, station_id: str
    ) -> Optional[object]:
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
                Zone.color.label("zone_color"),
            )
            .join(Zone, Station.zone_id == Zone.id)
            .where(
                Station.id == UUID(station_id),
                Station.deleted_at.is_(None),
            )
        )
        return result.first()

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
    async def get_device_for_station(
        session: AsyncSession, station_id: str
    ) -> Optional[Device]:
        result = await session.execute(
            select(Device).where(
                Device.station_id == UUID(station_id),
                Device.deleted_at.is_(None),
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_active_food_for_station(
        session: AsyncSession, station_id: str
    ) -> Optional[str]:
        from modules.foods.models import Food
        from modules.station_foods.models import StationFood

        result = await session.execute(
            select(Food.name)
            .join(StationFood, StationFood.food_id == Food.id)
            .where(
                StationFood.station_id == UUID(station_id),
                StationFood.active.is_(True),
            )
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None

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
    async def get_latest_telemetry_for_station(station_id: str) -> Optional[dict]:
        pipeline = [
            {"$match": {"station_id": station_id}},
            {"$sort": {"ingested_at": -1}},
            {"$limit": 1},
        ]
        cursor = get_collection(COLLECTION_TELEMETRY).aggregate(pipeline)
        async for doc in cursor:
            return doc
        return None

    @staticmethod
    async def get_system_latest_telemetry() -> Optional[dict]:
        """Returns the single most recent telemetry document across all stations."""
        return await get_collection(COLLECTION_TELEMETRY).find_one(
            {}, sort=[("ingested_at", -1)]
        )

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
    async def get_recent_events_for_station(
        station_id: str, limit: int = 5
    ) -> list[dict]:
        pipeline = [
            {"$match": {"station_id": station_id}},
            {"$sort": {"ingested_at": -1}},
            {"$limit": limit},
        ]
        cursor = get_collection(COLLECTION_IOT_EVENTS).aggregate(pipeline)
        return [doc async for doc in cursor]

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

    @staticmethod
    async def get_open_alert_count_for_station(station_id: str) -> int:
        pipeline = [
            {"$match": {"resolved": False, "station_id": station_id}},
            {"$count": "total"},
        ]
        cursor = get_collection(COLLECTION_ALERTS).aggregate(pipeline)
        async for doc in cursor:
            return doc["total"]
        return 0

    # ── GEO-4: Animals and Activity Feed ─────────────────────────────────────

    @staticmethod
    async def get_rfid_tags_for_station(
        station_id: str, cutoff: Optional[datetime] = None
    ) -> list[str]:
        """Distinct rfid_tags that visited this station within the time window."""
        match: dict = {"station_id": station_id, "rfid_tag": {"$ne": None}}
        if cutoff:
            match["ingested_at"] = {"$gte": cutoff}
        pipeline = [{"$match": match}, {"$group": {"_id": "$rfid_tag"}}]
        cursor = get_collection(COLLECTION_IOT_EVENTS).aggregate(pipeline)
        return [doc["_id"] async for doc in cursor]

    @staticmethod
    async def get_animals_by_rfid_tags(session: AsyncSession, rfid_tags: list[str]):
        """Return Animal rows whose rfid_tag is in the given list."""
        from modules.animals.models import Animal

        if not rfid_tags:
            return []
        result = await session.execute(
            select(Animal).where(
                Animal.rfid_tag.in_(rfid_tags),
                Animal.deleted_at.is_(None),
            )
        )
        return result.scalars().all()

    @staticmethod
    async def get_animal_rfid_stats(
        station_id: str,
        rfid_tags: list[str],
        cutoff: Optional[datetime] = None,
    ) -> dict[str, dict]:
        """Per rfid_tag: visit count, last visit, avg consumed_g."""
        if not rfid_tags:
            return {}
        match: dict = {"station_id": station_id, "rfid_tag": {"$in": rfid_tags}}
        if cutoff:
            match["ingested_at"] = {"$gte": cutoff}
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$rfid_tag",
                    "count": {"$sum": 1},
                    "last_visit": {"$max": "$ingested_at"},
                    "avg_consumed_g": {"$avg": "$consumed_g"},
                }
            },
        ]
        cursor = get_collection(COLLECTION_IOT_EVENTS).aggregate(pipeline)
        result: dict = {}
        async for doc in cursor:
            result[doc["_id"]] = {
                "count": doc["count"],
                "last_visit": doc.get("last_visit"),
                "avg_consumed_g": doc.get("avg_consumed_g"),
            }
        return result

    @staticmethod
    async def get_recent_iot_events_for_activity(
        station_id: str, limit: int
    ) -> list[dict]:
        """Most recent IoT events for a station (for activity feed)."""
        cursor = (
            get_collection(COLLECTION_IOT_EVENTS)
            .find({"station_id": station_id})
            .sort("ingested_at", -1)
            .limit(limit)
        )
        return [doc async for doc in cursor]

    @staticmethod
    async def get_recent_alerts_for_activity(
        station_id: str, limit: int
    ) -> list[dict]:
        """Most recent alerts for a station (for activity feed)."""
        cursor = (
            get_collection(COLLECTION_ALERTS)
            .find({"station_id": station_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        return [doc async for doc in cursor]

    # ── GEO-5: Global Stats ───────────────────────────────────────────────────

    @staticmethod
    async def get_station_avg_weights_bulk(
        cutoff: Optional[datetime] = None,
    ) -> dict[str, float]:
        """Average consumed_g per station_id for the given time window."""
        match: dict = {"station_id": {"$ne": None}, "consumed_g": {"$ne": None}}
        if cutoff:
            match["ingested_at"] = {"$gte": cutoff}
        pipeline = [
            {"$match": match},
            {"$group": {"_id": "$station_id", "avg": {"$avg": "$consumed_g"}}},
        ]
        cursor = get_collection(COLLECTION_IOT_EVENTS).aggregate(pipeline)
        result: dict[str, float] = {}
        async for doc in cursor:
            result[doc["_id"]] = doc["avg"]
        return result

    @staticmethod
    async def get_all_animals_with_rfid(session: AsyncSession) -> list:
        """All non-deleted animals that have a non-null rfid_tag."""
        from modules.animals.models import Animal

        result = await session.execute(
            select(Animal).where(
                Animal.rfid_tag.is_not(None),
                Animal.deleted_at.is_(None),
            )
        )
        return result.scalars().all()

    # ── GEO-6: Animal History ─────────────────────────────────────────────────

    # ── GEO-7: Station Events (paginated) ─────────────────────────────────────

    @staticmethod
    async def get_station_events_page(
        station_id: str,
        event_filter: str,
        cutoff: Optional[datetime],
        skip: int,
        limit: int,
    ) -> dict:
        """
        Paginated IoT events for a station.
        event_filter: "all" | "identified" | "unidentified"
        Returns dict with events list and all required counts.
        """
        coll = get_collection(COLLECTION_IOT_EVENTS)

        base_match: dict = {"station_id": station_id}
        if cutoff:
            base_match["ingested_at"] = {"$gte": cutoff}

        filtered_match = dict(base_match)
        if event_filter == "identified":
            filtered_match["rfid_tag"] = {"$ne": None}
        elif event_filter == "unidentified":
            filtered_match["$or"] = [
                {"rfid_tag": {"$exists": False}},
                {"rfid_tag": None},
            ]

        cursor = (
            coll.find(filtered_match)
            .sort("ingested_at", -1)
            .skip(skip)
            .limit(limit)
        )
        events = [doc async for doc in cursor]

        import asyncio as _asyncio
        filtered_total, all_total = await _asyncio.gather(
            coll.count_documents(filtered_match),
            coll.count_documents(base_match),
        )
        identified_match = dict(base_match) | {"rfid_tag": {"$ne": None}}
        identified_count = await coll.count_documents(identified_match)

        return {
            "events": events,
            "filtered_total": filtered_total,
            "all_total": all_total,
            "identified": identified_count,
            "unidentified": all_total - identified_count,
        }

    # ── GEO-6: Animal History ─────────────────────────────────────────────────

    @staticmethod
    async def get_animal_by_id(session: AsyncSession, animal_id: str):
        """Return Animal row by UUID, or None if not found/deleted."""
        from modules.animals.models import Animal

        result = await session.execute(
            select(Animal).where(
                Animal.id == UUID(animal_id),
                Animal.deleted_at.is_(None),
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_animal_feeding_timeline(
        rfid_tag: str,
        cutoff: Optional[datetime],
        limit: int = 50,
    ) -> list[dict]:
        """Latest IoT events for this RFID tag, sorted newest-first."""
        match: dict = {"rfid_tag": rfid_tag}
        if cutoff:
            match["ingested_at"] = {"$gte": cutoff}
        cursor = (
            get_collection(COLLECTION_IOT_EVENTS)
            .find(match)
            .sort("ingested_at", -1)
            .limit(limit)
        )
        return [doc async for doc in cursor]

    @staticmethod
    async def get_animal_weekly_activity(
        rfid_tag: str,
        cutoff: Optional[datetime],
    ) -> list[int]:
        """Visit count per weekday: index 0=Mon … 6=Sun."""
        match: dict = {"rfid_tag": rfid_tag}
        if cutoff:
            match["ingested_at"] = {"$gte": cutoff}
        pipeline = [
            {"$match": match},
            {"$project": {"dow": {"$dayOfWeek": "$ingested_at"}}},
            {"$group": {"_id": "$dow", "count": {"$sum": 1}}},
        ]
        cursor = get_collection(COLLECTION_IOT_EVENTS).aggregate(pipeline)
        # MongoDB dayOfWeek: 1=Sun, 2=Mon … 7=Sat → remap to 0=Mon … 6=Sun
        counts = [0] * 7
        async for doc in cursor:
            idx = (doc["_id"] - 2) % 7
            counts[idx] += doc["count"]
        return counts

    @staticmethod
    async def get_animal_station_visit_counts(
        rfid_tag: str,
        cutoff: Optional[datetime],
    ) -> dict[str, int]:
        """Total visits per station_id for this animal."""
        match: dict = {"rfid_tag": rfid_tag, "station_id": {"$ne": None}}
        if cutoff:
            match["ingested_at"] = {"$gte": cutoff}
        pipeline = [
            {"$match": match},
            {"$group": {"_id": "$station_id", "count": {"$sum": 1}}},
        ]
        cursor = get_collection(COLLECTION_IOT_EVENTS).aggregate(pipeline)
        return {doc["_id"]: doc["count"] async for doc in cursor}

    @staticmethod
    async def get_last_rfid_event_for_animal(rfid_tag: str) -> Optional[dict]:
        """Most recent IoT event for this RFID tag from MongoDB, or None."""
        return await get_collection(COLLECTION_IOT_EVENTS).find_one(
            {"rfid_tag": rfid_tag},
            sort=[("ingested_at", -1)],
        )

    @staticmethod
    async def get_station_with_zone(
        session: AsyncSession,
        station_id: str,
    ) -> Optional[tuple]:
        """Return (Station, Zone) row or None."""
        result = await session.execute(
            select(Station, Zone)
            .join(Zone, Station.zone_id == Zone.id)
            .where(
                Station.id == UUID(station_id),
                Station.deleted_at.is_(None),
            )
        )
        return result.first()

    @staticmethod
    async def get_animal_station_paths(
        rfid_tags: list[str],
        cutoff: Optional[datetime] = None,
    ) -> dict[str, list[str]]:
        """
        For each rfid_tag: ordered list of station_ids visited (chronological).
        Sorted by ingested_at so the path reflects real movement order.
        """
        if not rfid_tags:
            return {}
        match: dict = {
            "rfid_tag": {"$in": rfid_tags},
            "station_id": {"$ne": None},
        }
        if cutoff:
            match["ingested_at"] = {"$gte": cutoff}
        pipeline = [
            {"$match": match},
            {"$sort": {"ingested_at": 1}},
            {"$group": {"_id": "$rfid_tag", "stations": {"$push": "$station_id"}}},
        ]
        cursor = get_collection(COLLECTION_IOT_EVENTS).aggregate(pipeline)
        result: dict[str, list[str]] = {}
        async for doc in cursor:
            result[doc["_id"]] = doc["stations"]
        return result
