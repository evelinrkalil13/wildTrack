from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from shared.enums import TimeFilter


def _dedup_consecutive(items: list[str]) -> list[str]:
    """Collapse consecutive duplicate station_ids: [A,A,B,B,A] → [A,B,A]."""
    out: list[str] = []
    for item in items:
        if not out or out[-1] != item:
            out.append(item)
    return out


def get_time_cutoff(time_filter: TimeFilter) -> Optional[datetime]:
    now = datetime.now(timezone.utc)
    cutoffs = {
        TimeFilter.h24: timedelta(hours=24),
        TimeFilter.d7: timedelta(days=7),
        TimeFilter.d30: timedelta(days=30),
    }
    delta = cutoffs.get(time_filter)
    return (now - delta) if delta else None


@dataclass
class StationCounts:
    visitas_total: int = 0
    visitas_identificadas: int = 0
    visitas_sin_identificar: int = 0


@dataclass
class StationDetailStats:
    visitas_total: int = 0
    visitas_identificadas: int = 0
    visitas_sin_identificar: int = 0
    peso_promedio_g: Optional[float] = None
    peso_mediana_g: Optional[float] = None
    visitas_por_dia: list = field(default_factory=lambda: [0] * 7)


class GeoportalAggregationService:
    @staticmethod
    async def compute_station_counts(
        time_filter: TimeFilter,
    ) -> dict[str, StationCounts]:
        """
        Returns dict keyed by station_id with visit counts.
        Used by: GET /geoportal/stations
        """
        from infrastructure.mongodb import COLLECTION_IOT_EVENTS, get_collection

        cutoff = get_time_cutoff(time_filter)
        match: dict = {"station_id": {"$ne": None}}
        if cutoff:
            match["ingested_at"] = {"$gte": cutoff}

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$station_id",
                    "total": {"$sum": 1},
                    "identified": {
                        "$sum": {
                            "$cond": [{"$ifNull": ["$rfid_tag", False]}, 1, 0]
                        }
                    },
                }
            },
        ]
        cursor = get_collection(COLLECTION_IOT_EVENTS).aggregate(pipeline)
        result: dict[str, StationCounts] = {}
        async for doc in cursor:
            total = doc["total"]
            identified = doc["identified"]
            result[doc["_id"]] = StationCounts(
                visitas_total=total,
                visitas_identificadas=identified,
                visitas_sin_identificar=total - identified,
            )
        return result

    @staticmethod
    async def compute_station_detail_stats(
        station_id: str,
        time_filter: TimeFilter,
    ) -> StationDetailStats:
        """
        Returns full stats for a single station including weight and weekly frequency.
        Used by: GET /geoportal/stations/{id}
        """
        from infrastructure.mongodb import COLLECTION_IOT_EVENTS, get_collection

        cutoff = get_time_cutoff(time_filter)
        match: dict = {"station_id": station_id}
        if cutoff:
            match["ingested_at"] = {"$gte": cutoff}

        pipeline = [
            {"$match": match},
            {
                "$project": {
                    "rfid_tag": 1,
                    "consumed_g": 1,
                    # MongoDB dayOfWeek: 1=Sun, 2=Mon, ..., 7=Sat
                    "dow": {"$dayOfWeek": "$ingested_at"},
                }
            },
        ]
        cursor = get_collection(COLLECTION_IOT_EVENTS).aggregate(pipeline)

        total = 0
        identified = 0
        consumed_values: list[float] = []
        # Remap to 0=Mon..6=Sun: dow 1(Sun)→6, 2(Mon)→0, ..., 7(Sat)→5
        day_counts = [0] * 7

        async for doc in cursor:
            total += 1
            if doc.get("rfid_tag"):
                identified += 1
            cg = doc.get("consumed_g")
            if cg is not None:
                try:
                    consumed_values.append(float(cg))
                except (TypeError, ValueError):
                    pass
            dow = doc.get("dow", 1)  # 1-7
            idx = (dow - 2) % 7
            day_counts[idx] += 1

        peso_promedio_g = None
        peso_mediana_g = None
        if consumed_values:
            peso_promedio_g = round(sum(consumed_values) / len(consumed_values), 1)
            sorted_vals = sorted(consumed_values)
            n = len(sorted_vals)
            if n % 2 == 0:
                peso_mediana_g = round(
                    (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2, 1
                )
            else:
                peso_mediana_g = round(sorted_vals[n // 2], 1)

        return StationDetailStats(
            visitas_total=total,
            visitas_identificadas=identified,
            visitas_sin_identificar=total - identified,
            peso_promedio_g=peso_promedio_g,
            peso_mediana_g=peso_mediana_g,
            visitas_por_dia=day_counts,
        )

    # ── GEO-4 ────────────────────────────────────────────────────────────────

    @staticmethod
    async def compute_station_animals(
        session,
        station_id: str,
        time_filter: TimeFilter,
    ) -> list:
        """Animals that visited this station, sorted by visit count desc."""
        from modules.geoportal.repository import GeoportalRepository
        from modules.geoportal.schemas import GeoportalAnimalRead

        cutoff = get_time_cutoff(time_filter)
        rfid_tags = await GeoportalRepository.get_rfid_tags_for_station(
            station_id, cutoff
        )
        if not rfid_tags:
            return []

        animals = await GeoportalRepository.get_animals_by_rfid_tags(
            session, rfid_tags
        )
        rfid_stats = await GeoportalRepository.get_animal_rfid_stats(
            station_id, rfid_tags, cutoff
        )

        result = []
        for animal in animals:
            tag = animal.rfid_tag
            stats = rfid_stats.get(tag, {})
            avg = stats.get("avg_consumed_g")
            result.append(
                GeoportalAnimalRead(
                    animal_id=str(animal.id),
                    rfid_tag=tag,
                    species=animal.species,
                    sex=animal.sex.value
                    if hasattr(animal.sex, "value")
                    else str(animal.sex),
                    estimated_age=animal.estimated_age,
                    notes=animal.notes,
                    registered_at=animal.created_at,
                    total_visits=stats.get("count", 0),
                    last_visit=stats.get("last_visit"),
                    avg_consumed_g=round(avg, 1) if avg is not None else None,
                )
            )
        result.sort(key=lambda a: a.total_visits, reverse=True)
        return result

    @staticmethod
    async def build_activity_feed(
        station_id: str,
        limit: int = 20,
    ) -> list:
        """Unified chronological feed: IoT events + alerts + latest telemetry."""
        from modules.geoportal.repository import GeoportalRepository
        from modules.geoportal.schemas import ActivityItem, ActivityItemType

        fetch = max(limit, 10)
        iot_docs = await GeoportalRepository.get_recent_iot_events_for_activity(
            station_id, fetch
        )
        alert_docs = await GeoportalRepository.get_recent_alerts_for_activity(
            station_id, fetch
        )
        telemetry_doc = await GeoportalRepository.get_latest_telemetry_for_station(
            station_id
        )

        items: list[ActivityItem] = []

        for doc in iot_docs:
            ts = doc.get("ingested_at")
            if not isinstance(ts, datetime):
                continue
            rfid = doc.get("rfid_tag")
            consumed = doc.get("consumed_g")
            media: list[str] = doc.get("media_urls") or []
            photos = doc.get("photos_count") or len(media)

            # One entry per event: rfid_read if identified, else feeding
            if rfid:
                desc = f"RFID leído: {rfid}"
                if consumed is not None:
                    try:
                        desc += f" · {float(consumed):.0f} g"
                    except (TypeError, ValueError):
                        pass
                item_type = ActivityItemType.rfid_read
            else:
                desc = "Alimentación"
                if consumed is not None:
                    try:
                        desc += f" · {float(consumed):.0f} g consumidos"
                    except (TypeError, ValueError):
                        pass
                item_type = ActivityItemType.feeding

            items.append(
                ActivityItem(
                    item_type=item_type,
                    timestamp=ts,
                    description=desc,
                    rfid_tag=rfid,
                    media_urls=media,
                )
            )
            if photos > 0 and media:
                items.append(
                    ActivityItem(
                        item_type=ActivityItemType.photo,
                        timestamp=ts,
                        description=f"Foto capturada ({photos})",
                        media_urls=media,
                    )
                )

        for doc in alert_docs:
            ts = doc.get("created_at") or doc.get("ingested_at")
            if not isinstance(ts, datetime):
                continue
            alert_type = doc.get("alert_type", "alerta")
            severity = doc.get("severity", "warning")
            items.append(
                ActivityItem(
                    item_type=ActivityItemType.alert,
                    timestamp=ts,
                    description=f"Alerta: {alert_type}",
                    severity=severity,
                )
            )

        if telemetry_doc:
            ts = telemetry_doc.get("ingested_at") or telemetry_doc.get("timestamp")
            if isinstance(ts, datetime):
                temp = telemetry_doc.get("temperature_c")
                hum = telemetry_doc.get("humidity_pct")
                parts = ["Telemetría recibida"]
                if temp is not None:
                    parts.append(f"{temp:.1f} °C")
                if hum is not None:
                    parts.append(f"{hum:.0f}% HR")
                items.append(
                    ActivityItem(
                        item_type=ActivityItemType.telemetry,
                        timestamp=ts,
                        description=" · ".join(parts),
                        severity="info",
                    )
                )

        items.sort(key=lambda x: x.timestamp, reverse=True)
        return items[:limit]

    # ── GEO-5 ────────────────────────────────────────────────────────────────

    @staticmethod
    def compute_sector_summaries(
        station_rows: list,
        counts_map: dict,
        alert_map: dict,
        avg_weights_map: dict,
    ) -> list:
        """
        Aggregate station-level data up to zone level.
        Pure Python — all I/O has already been fetched by the caller.
        """
        from modules.geoportal.schemas import SectorStatRow

        zones: dict[str, dict] = {}
        zone_stations: dict[str, list] = defaultdict(list)

        for row in station_rows:
            zid = str(row.zone_id)
            if zid not in zones:
                zones[zid] = {"zone_name": row.zone_name, "zone_color": row.zone_color}
            zone_stations[zid].append(row)

        result = []
        for zid, rows in zone_stations.items():
            visitas = identificados = sin_id = en_alerta = 0
            w_num = 0.0
            w_den = 0

            for row in rows:
                sid = str(row.station_id)
                counts = counts_map.get(sid)
                if counts:
                    visitas += counts.visitas_total
                    identificados += counts.visitas_identificadas
                    sin_id += counts.visitas_sin_identificar
                if alert_map.get(sid, 0) > 0:
                    en_alerta += 1
                avg_w = avg_weights_map.get(sid)
                if avg_w is not None and counts and counts.visitas_total > 0:
                    w_num += avg_w * counts.visitas_total
                    w_den += counts.visitas_total

            zm = zones[zid]
            result.append(
                SectorStatRow(
                    zone_id=zid,
                    zone_name=zm["zone_name"],
                    zone_color=zm["zone_color"],
                    num_estaciones=len(rows),
                    visitas=visitas,
                    identificados=identificados,
                    sin_identificar=sin_id,
                    pct_sin_id=round(sin_id / visitas * 100, 1) if visitas > 0 else 0.0,
                    peso_promedio_g=round(w_num / w_den, 1) if w_den > 0 else None,
                    en_alerta=en_alerta,
                )
            )

        result.sort(key=lambda s: s.visitas, reverse=True)
        return result

    # ── GEO-6 ────────────────────────────────────────────────────────────────

    @staticmethod
    async def compute_animal_history(
        animal,
        time_filter: "TimeFilter",
        station_rows: list,
    ):
        """
        Build full feeding history for one animal.
        station_rows: result of GeoportalRepository.list_all_stations_with_zones()
        """
        import asyncio
        from modules.geoportal.repository import GeoportalRepository
        from modules.geoportal.schemas import (
            AnimalHistoryResponse,
            FeedingEvent,
            FeederRankItem,
            TraceStop,
        )

        cutoff = get_time_cutoff(time_filter)
        rfid_tag = animal.rfid_tag

        station_name_map: dict[str, str] = {
            str(r.station_id): r.station_name for r in station_rows
        }
        station_coord_map: dict[str, tuple[float, float]] = {
            str(r.station_id): (float(r.latitude), float(r.longitude))
            for r in station_rows
        }

        timeline_docs, weekly, visit_counts, paths_map = await asyncio.gather(
            GeoportalRepository.get_animal_feeding_timeline(rfid_tag, cutoff, 50),
            GeoportalRepository.get_animal_weekly_activity(rfid_tag, cutoff),
            GeoportalRepository.get_animal_station_visit_counts(rfid_tag, cutoff),
            GeoportalRepository.get_animal_station_paths([rfid_tag], cutoff),
        )

        raw_path = paths_map.get(rfid_tag, [])
        deduped = _dedup_consecutive(raw_path)

        # KPIs
        total_alimentaciones = sum(visit_counts.values())
        total_estaciones = len(visit_counts)

        dates: set = set()
        for doc in timeline_docs:
            ts = doc.get("ingested_at")
            if isinstance(ts, datetime):
                dates.add(ts.date())
        dias_activo = len(dates)

        weights = [
            float(doc["consumed_g"])
            for doc in timeline_docs
            if doc.get("consumed_g") is not None
        ]
        peso_promedio_g = round(sum(weights) / len(weights), 1) if weights else None

        # Feeder ranking
        total_v = total_alimentaciones or 1
        ranking = sorted(visit_counts.items(), key=lambda x: x[1], reverse=True)
        feeder_ranking = [
            FeederRankItem(
                station_id=sid,
                station_name=station_name_map.get(sid, sid),
                visits=count,
                pct=round(count / total_v * 100, 1),
                is_primary=(i == 0),
            )
            for i, (sid, count) in enumerate(ranking)
        ]

        # Timeline
        timeline: list[FeedingEvent] = []
        for doc in timeline_docs:
            ts = doc.get("ingested_at")
            if not isinstance(ts, datetime):
                continue
            sid = doc.get("station_id", "")
            timeline.append(
                FeedingEvent(
                    event_id=doc.get("event_id", ""),
                    station_id=sid,
                    station_name=station_name_map.get(sid, sid),
                    timestamp=ts,
                    consumed_g=doc.get("consumed_g"),
                    temperature_c=doc.get("temperature_c"),
                    humidity_pct=doc.get("humidity_pct"),
                    media_urls=doc.get("media_urls") or [],
                )
            )

        # Trace path — use latest timestamp per station from the timeline
        station_latest_ts: dict[str, datetime] = {}
        for doc in timeline_docs:
            ts = doc.get("ingested_at")
            sid = doc.get("station_id", "")
            if isinstance(ts, datetime) and sid:
                if sid not in station_latest_ts or ts > station_latest_ts[sid]:
                    station_latest_ts[sid] = ts

        trace_path: list[TraceStop] = []
        for sid in deduped:
            coords = station_coord_map.get(sid)
            ts = station_latest_ts.get(sid)
            if coords is None or ts is None:
                continue
            trace_path.append(
                TraceStop(
                    station_id=sid,
                    station_name=station_name_map.get(sid, sid),
                    lat=coords[0],
                    lng=coords[1],
                    timestamp=ts,
                )
            )

        # Insight text
        if feeder_ranking and feeder_ranking[0].pct >= 66:
            insight_text = (
                f"Preferencia marcada: {feeder_ranking[0].pct:.0f}% de las visitas"
                f" en {feeder_ranking[0].station_name}"
            )
        elif total_estaciones > 1:
            insight_text = f"Uso distribuido entre {total_estaciones} comederos"
        else:
            insight_text = "Registrado en un único comedero"

        sex = animal.sex.value if hasattr(animal.sex, "value") else str(animal.sex)

        return AnimalHistoryResponse(
            animal_id=str(animal.id),
            rfid_tag=rfid_tag,
            species=animal.species,
            sex=sex,
            estimated_age=animal.estimated_age,
            notes=animal.notes,
            total_alimentaciones=total_alimentaciones,
            total_estaciones=total_estaciones,
            dias_activo=dias_activo,
            peso_promedio_g=peso_promedio_g,
            actividad_semanal=weekly,
            feeder_ranking=feeder_ranking,
            timeline=timeline,
            trace_path=trace_path,
            insight_text=insight_text,
            time_filter=time_filter.value,
        )

    @staticmethod
    def compute_animal_movements(
        animals: list,
        paths_map: dict[str, list[str]],
        station_name_map: dict[str, str],
    ) -> list:
        """
        Build per-animal movement paths across stations.
        Pure Python — all I/O has already been fetched by the caller.
        """
        from modules.geoportal.schemas import AnimalMovement

        result = []
        for animal in animals:
            raw_path = paths_map.get(animal.rfid_tag, [])
            deduped = _dedup_consecutive(raw_path)
            distinct = len(set(raw_path))
            path_names = [station_name_map.get(sid, sid) for sid in deduped]
            sex = (
                animal.sex.value if hasattr(animal.sex, "value") else str(animal.sex)
            )
            result.append(
                AnimalMovement(
                    animal_id=str(animal.id),
                    rfid_tag=animal.rfid_tag,
                    species=animal.species,
                    sex=sex,
                    distinct_stations=distinct,
                    path=deduped,
                    path_names=path_names,
                )
            )

        result.sort(key=lambda m: m.distinct_stations, reverse=True)
        return result
