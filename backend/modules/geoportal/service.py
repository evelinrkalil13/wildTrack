from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from modules.geoportal.aggregation import GeoportalAggregationService, get_time_cutoff
from modules.geoportal.repository import GeoportalRepository
import math

from modules.geoportal.schemas import (
    ActivityItem,
    AnimalHistoryResponse,
    GeoportalAnimalRead,
    GeoportalDeviceInfo,
    GeoportalRecentEvent,
    GeoportalStationDetail,
    GeoportalStationMapItem,
    GeoportalStatsResponse,
    GeoportalTelemetry,
    StationEventDetail,
    StationEventsResponse,
    StationStatRow,
)
from shared.enums import DeviceStatus, TimeFilter


def _build_device(device) -> GeoportalDeviceInfo:
    return GeoportalDeviceInfo(
        device_id=str(device.id),
        serial_number=device.serial_number,
        status=device.status,
        last_seen=device.last_seen,
    )


def _build_telemetry(doc: dict) -> Optional[GeoportalTelemetry]:
    ts = doc.get("ingested_at") or doc.get("timestamp")
    if ts is None or not isinstance(ts, datetime):
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
    async def list_stations(
        session: AsyncSession,
        time_filter: TimeFilter = TimeFilter.d7,
    ) -> list[GeoportalStationMapItem]:
        station_rows = await GeoportalRepository.list_all_stations_with_zones(session)
        if not station_rows:
            return []

        device_map = await GeoportalRepository.list_assigned_devices_by_station(session)
        alert_map = await GeoportalRepository.get_open_alert_counts_by_station()
        counts_map = await GeoportalAggregationService.compute_station_counts(time_filter)

        results: list[GeoportalStationMapItem] = []
        for row in station_rows:
            station_id_str = str(row.station_id)
            device = device_map.get(station_id_str)
            open_alerts = alert_map.get(station_id_str, 0)
            counts = counts_map.get(station_id_str)

            is_live = (
                device is not None and device.status == DeviceStatus.online
            )
            device_status = device.status if device else None

            results.append(
                GeoportalStationMapItem(
                    station_id=station_id_str,
                    station_code=row.station_code,
                    station_name=row.station_name,
                    status=row.station_status,
                    latitude=float(row.latitude),
                    longitude=float(row.longitude),
                    zone_id=str(row.zone_id),
                    zone_name=row.zone_name,
                    zone_color=row.zone_color,
                    device_status=device_status,
                    open_alerts_count=open_alerts,
                    is_live=is_live,
                    visitas_total=counts.visitas_total if counts else 0,
                    visitas_identificadas=counts.visitas_identificadas if counts else 0,
                    visitas_sin_identificar=counts.visitas_sin_identificar if counts else 0,
                )
            )
        return results

    @staticmethod
    async def get_station_detail(
        session: AsyncSession,
        station_id: str,
        time_filter: TimeFilter = TimeFilter.d7,
    ) -> Optional[GeoportalStationDetail]:
        row = await GeoportalRepository.get_station_with_zone_by_id(session, station_id)
        if row is None:
            return None

        device = await GeoportalRepository.get_device_for_station(session, station_id)
        telemetry_doc = await GeoportalRepository.get_latest_telemetry_for_station(
            station_id
        )
        event_docs = await GeoportalRepository.get_recent_events_for_station(
            station_id, limit=5
        )
        open_alerts = await GeoportalRepository.get_open_alert_count_for_station(
            station_id
        )
        food_type = await GeoportalRepository.get_active_food_for_station(
            session, station_id
        )
        stats = await GeoportalAggregationService.compute_station_detail_stats(
            station_id, time_filter
        )

        is_live = device is not None and device.status == DeviceStatus.online
        device_status = device.status if device else None
        telemetry = _build_telemetry(telemetry_doc) if telemetry_doc else None
        recent_events = [
            e for doc in event_docs if (e := _build_event(doc)) is not None
        ]

        return GeoportalStationDetail(
            station_id=str(row.station_id),
            station_code=row.station_code,
            station_name=row.station_name,
            status=row.station_status,
            latitude=float(row.latitude),
            longitude=float(row.longitude),
            zone_id=str(row.zone_id),
            zone_name=row.zone_name,
            zone_color=row.zone_color,
            device_status=device_status,
            open_alerts_count=open_alerts,
            is_live=is_live,
            visitas_total=stats.visitas_total,
            visitas_identificadas=stats.visitas_identificadas,
            visitas_sin_identificar=stats.visitas_sin_identificar,
            food_type=food_type,
            device=_build_device(device) if device else None,
            latest_telemetry=telemetry,
            peso_promedio_g=stats.peso_promedio_g,
            peso_mediana_g=stats.peso_mediana_g,
            visitas_por_dia=stats.visitas_por_dia,
            recent_events=recent_events,
        )

    # ── GEO-4 ────────────────────────────────────────────────────────────────

    @staticmethod
    async def list_station_animals(
        session: AsyncSession,
        station_id: str,
        time_filter: TimeFilter = TimeFilter.d7,
    ) -> list[GeoportalAnimalRead]:
        return await GeoportalAggregationService.compute_station_animals(
            session, station_id, time_filter
        )

    @staticmethod
    async def list_station_activity(
        station_id: str,
        limit: int = 20,
    ) -> list[ActivityItem]:
        return await GeoportalAggregationService.build_activity_feed(
            station_id, limit
        )

    # ── GEO-7 ────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_station_events(
        session: AsyncSession,
        station_id: str,
        page: int = 1,
        page_size: int = 20,
        event_filter: str = "all",
        time_filter: TimeFilter = TimeFilter.d7,
    ) -> Optional[StationEventsResponse]:
        row = await GeoportalRepository.get_station_with_zone_by_id(session, station_id)
        if row is None:
            return None

        cutoff = get_time_cutoff(time_filter)
        skip = (page - 1) * page_size

        data = await GeoportalRepository.get_station_events_page(
            station_id, event_filter, cutoff, skip, page_size
        )

        # Enrich events with animal data from PostgreSQL
        rfid_tags = [
            d["rfid_tag"] for d in data["events"] if d.get("rfid_tag")
        ]
        animals_by_rfid: dict = {}
        if rfid_tags:
            animals = await GeoportalRepository.get_animals_by_rfid_tags(
                session, rfid_tags
            )
            animals_by_rfid = {a.rfid_tag: a for a in animals}

        events: list[StationEventDetail] = []
        for doc in data["events"]:
            ts = doc.get("ingested_at")
            if not isinstance(ts, datetime):
                continue
            rfid = doc.get("rfid_tag")
            animal = animals_by_rfid.get(rfid) if rfid else None
            sex_val = None
            if animal:
                sex_val = (
                    animal.sex.value
                    if hasattr(animal.sex, "value")
                    else str(animal.sex)
                )
            events.append(
                StationEventDetail(
                    event_id=doc.get("event_id", ""),
                    timestamp=ts,
                    rfid_tag=rfid,
                    animal_id=str(animal.id) if animal else None,
                    animal_species=animal.species if animal else None,
                    animal_sex=sex_val,
                    consumed_g=doc.get("consumed_g"),
                    temperature_c=doc.get("temperature_c"),
                    humidity_pct=doc.get("humidity_pct"),
                    media_urls=doc.get("media_urls") or [],
                    is_identified=animal is not None,
                )
            )

        filtered_total = data["filtered_total"]
        pages = max(1, math.ceil(filtered_total / page_size))

        return StationEventsResponse(
            station_id=station_id,
            station_name=row.station_name,
            total=filtered_total,
            identificadas=data["identified"],
            sin_identificar=data["unidentified"],
            page=page,
            pages=pages,
            events=events,
        )

    # ── GEO-6 ────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_animal_history(
        session: AsyncSession,
        animal_id: str,
        time_filter: TimeFilter = TimeFilter.all,
    ) -> Optional[AnimalHistoryResponse]:
        animal = await GeoportalRepository.get_animal_by_id(session, animal_id)
        if animal is None or animal.rfid_tag is None:
            return None

        station_rows = await GeoportalRepository.list_all_stations_with_zones(session)
        return await GeoportalAggregationService.compute_animal_history(
            animal, time_filter, station_rows
        )

    # ── GEO-5 ────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_global_stats(
        session: AsyncSession,
        time_filter: TimeFilter = TimeFilter.d7,
    ) -> GeoportalStatsResponse:
        cutoff = get_time_cutoff(time_filter)

        station_rows = await GeoportalRepository.list_all_stations_with_zones(session)
        counts_map = await GeoportalAggregationService.compute_station_counts(time_filter)
        alert_map = await GeoportalRepository.get_open_alert_counts_by_station()
        avg_weights = await GeoportalRepository.get_station_avg_weights_bulk(cutoff)

        animals = await GeoportalRepository.get_all_animals_with_rfid(session)
        rfid_tags = [a.rfid_tag for a in animals]
        paths_map = (
            await GeoportalRepository.get_animal_station_paths(rfid_tags, cutoff)
            if rfid_tags
            else {}
        )

        station_name_map = {str(r.station_id): r.station_name for r in station_rows}

        total_visitas = 0
        total_sin_chip = 0
        estaciones: list[StationStatRow] = []

        for row in station_rows:
            sid = str(row.station_id)
            counts = counts_map.get(sid)
            v = counts.visitas_total if counts else 0
            idf = counts.visitas_identificadas if counts else 0
            noid = counts.visitas_sin_identificar if counts else 0
            total_visitas += v
            total_sin_chip += noid
            avg_w = avg_weights.get(sid)
            estaciones.append(
                StationStatRow(
                    station_id=sid,
                    station_code=row.station_code,
                    station_name=row.station_name,
                    zone_id=str(row.zone_id),
                    zone_name=row.zone_name,
                    zone_color=row.zone_color,
                    visitas=v,
                    identificados=idf,
                    sin_identificar=noid,
                    peso_promedio_g=round(avg_w, 1) if avg_w is not None else None,
                    status=row.station_status,
                    open_alerts=alert_map.get(sid, 0),
                )
            )

        estaciones.sort(key=lambda s: s.visitas, reverse=True)

        sectores = GeoportalAggregationService.compute_sector_summaries(
            station_rows, counts_map, alert_map, avg_weights
        )
        animales = GeoportalAggregationService.compute_animal_movements(
            animals, paths_map, station_name_map
        )

        total_sectores = len({str(r.zone_id) for r in station_rows})

        return GeoportalStatsResponse(
            time_filter=time_filter.value,
            total_estaciones=len(station_rows),
            total_sectores=total_sectores,
            total_animales_con_chip=len(animals),
            total_visitas=total_visitas,
            avistamientos_sin_chip=total_sin_chip,
            estaciones=estaciones,
            sectores=sectores,
            animales_con_chip=animales,
        )
