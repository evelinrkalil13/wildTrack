import enum as _enum
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


class GeoportalStationMapItem(BaseModel):
    """Lean — only map and sidebar data. Kept small and stable."""
    station_id: str
    station_code: str
    station_name: str
    status: StationStatus
    latitude: float
    longitude: float
    zone_id: str
    zone_name: str
    zone_color: str = "#52b788"
    device_status: Optional[DeviceStatus] = None
    open_alerts_count: int = 0
    is_live: bool = False
    visitas_total: int = 0
    visitas_identificadas: int = 0
    visitas_sin_identificar: int = 0


# Backward-compat alias used by existing tests
GeoportalStationRead = GeoportalStationMapItem


class GeoportalStationDetail(GeoportalStationMapItem):
    """Full detail fetched on-demand when a station is selected."""
    food_type: Optional[str] = None
    device: Optional[GeoportalDeviceInfo] = None
    latest_telemetry: Optional[GeoportalTelemetry] = None
    peso_promedio_g: Optional[float] = None
    peso_mediana_g: Optional[float] = None
    visitas_por_dia: list[int] = []  # 7 values Mon(0)–Sun(6)
    recent_events: list[GeoportalRecentEvent] = []


# ── GEO-4: Animals and Activity Feed ─────────────────────────────────────────

class ActivityItemType(str, _enum.Enum):
    feeding = "feeding"
    rfid_read = "rfid_read"
    photo = "photo"
    alert = "alert"
    telemetry = "telemetry"


class ActivityItem(BaseModel):
    item_type: ActivityItemType
    timestamp: datetime
    description: str
    rfid_tag: Optional[str] = None
    animal_species: Optional[str] = None
    media_urls: list[str] = []
    severity: Optional[str] = None  # "info" | "warning" | "critical"


class GeoportalAnimalRead(BaseModel):
    animal_id: str
    rfid_tag: str
    species: str
    sex: str
    estimated_age: Optional[str] = None
    notes: Optional[str] = None
    registered_at: datetime
    total_visits: int = 0
    last_visit: Optional[datetime] = None
    avg_consumed_g: Optional[float] = None


# ── GEO-5: Global Stats ───────────────────────────────────────────────────────

class StationStatRow(BaseModel):
    station_id: str
    station_code: str
    station_name: str
    zone_id: str
    zone_name: str
    zone_color: str
    visitas: int
    identificados: int
    sin_identificar: int
    peso_promedio_g: Optional[float] = None
    status: StationStatus
    open_alerts: int


class SectorStatRow(BaseModel):
    zone_id: str
    zone_name: str
    zone_color: str
    num_estaciones: int
    visitas: int
    identificados: int
    sin_identificar: int
    pct_sin_id: float
    peso_promedio_g: Optional[float] = None
    en_alerta: int


class AnimalMovement(BaseModel):
    animal_id: str
    rfid_tag: str
    species: str
    sex: str
    distinct_stations: int
    path: list[str]        # station_ids deduped-consecutive chronological
    path_names: list[str]  # human-readable station names


class GeoportalStatsResponse(BaseModel):
    time_filter: str
    total_estaciones: int
    total_sectores: int
    total_animales_con_chip: int
    total_visitas: int
    avistamientos_sin_chip: int
    estaciones: list[StationStatRow]
    sectores: list[SectorStatRow]
    animales_con_chip: list[AnimalMovement]


# ── GEO-6: Animal Feeding Dashboard ──────────────────────────────────────────

class FeedingEvent(BaseModel):
    event_id: str
    station_id: str
    station_name: str
    timestamp: datetime
    consumed_g: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    media_urls: list[str] = []


class FeederRankItem(BaseModel):
    station_id: str
    station_name: str
    visits: int
    pct: float
    is_primary: bool


class TraceStop(BaseModel):
    station_id: str
    station_name: str
    lat: float
    lng: float
    timestamp: datetime


# ── GEO-7: Station Visits Modal ───────────────────────────────────────────────

class StationEventDetail(BaseModel):
    event_id: str
    timestamp: datetime
    rfid_tag: Optional[str] = None
    animal_id: Optional[str] = None
    animal_species: Optional[str] = None
    animal_sex: Optional[str] = None
    consumed_g: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    media_urls: list[str] = []
    is_identified: bool = False


class StationEventsResponse(BaseModel):
    station_id: str
    station_name: str
    total: int          # matches current filter (for pagination)
    identificadas: int  # always full count regardless of filter
    sin_identificar: int
    page: int
    pages: int
    events: list[StationEventDetail]


class AnimalHistoryResponse(BaseModel):
    animal_id: str
    rfid_tag: str
    species: str
    sex: str
    estimated_age: Optional[str] = None
    notes: Optional[str] = None
    total_alimentaciones: int
    total_estaciones: int
    dias_activo: int
    peso_promedio_g: Optional[float] = None
    actividad_semanal: list[int]  # 7 values Mon(0)–Sun(6)
    feeder_ranking: list[FeederRankItem]
    timeline: list[FeedingEvent]  # latest 50
    trace_path: list[TraceStop]
    insight_text: str
    time_filter: str


# ── GEO-9: Darwin Core Species Sheet ─────────────────────────────────────────

class GbifTaxonomy(BaseModel):
    kingdom: Optional[str] = None
    phylum: Optional[str] = None
    taxon_class: Optional[str] = None        # "class" is a Python keyword
    order: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None
    specific_epithet: Optional[str] = None
    scientific_name: Optional[str] = None
    scientific_name_authorship: Optional[str] = None
    taxon_rank: Optional[str] = None
    vernacular_name: Optional[str] = None
    gbif_usage_key: Optional[int] = None
    gbif_confidence: Optional[int] = None
    gbif_match_type: Optional[str] = None


class DarwinCoreObservation(BaseModel):
    # Occurrence
    occurrence_id: str
    catalog_number: Optional[str] = None
    basis_of_record: str
    event_date: Optional[str] = None
    recorded_by: str
    sex: Optional[str] = None
    life_stage: Optional[str] = None
    occurrence_remarks: Optional[str] = None
    individual_count: int
    # Location
    decimal_latitude: Optional[float] = None
    decimal_longitude: Optional[float] = None
    geodetic_datum: str
    coordinate_uncertainty_in_meters: int
    country: Optional[str] = None
    state_province: Optional[str] = None
    municipality: Optional[str] = None
    locality: Optional[str] = None
    location_remarks: Optional[str] = None
    # Record-level
    institution_code: str
    collection_code: str
    dataset_name: str
    rights_holder: str
    license: str
    nomenclatural_code: str


class TaxonomySource(BaseModel):
    provider: str
    url: Optional[str] = None
    api_url: Optional[str] = None
    license: str


class ObservationSource(BaseModel):
    provider: str
    platform: str


class DarwinCoreSources(BaseModel):
    taxonomy: TaxonomySource
    observation: ObservationSource


class DarwinCoreResponse(BaseModel):
    animal_id: str
    species: str
    source_status: str       # "ok" | "fuzzy_match" | "not_found" | "unavailable"
    taxonomy: Optional[GbifTaxonomy] = None
    observation: DarwinCoreObservation
    sources: DarwinCoreSources
    generated_at: datetime
