import type { DeviceStatus, StationStatus } from "@/api/types/enums";

export type TimePeriod = "24h" | "7d" | "30d" | "all";

export interface GeoportalDeviceInfo {
  device_id: string;
  serial_number: string;
  status: DeviceStatus;
  last_seen: string | null;
}

export interface GeoportalTelemetry {
  temperature_c: number | null;
  humidity_pct: number | null;
  wifi_rssi_dbm: number | null;
  firmware_version: string | null;
  timestamp: string;
}

export interface GeoportalRecentEvent {
  event_id: string;
  timestamp: string;
  rfid_tag: string | null;
  consumed_g: number | null;
  temperature_c: number | null;
  humidity_pct: number | null;
  photos_count: number;
  media_urls: string[];
}

/** Lean — only map and sidebar data. */
export interface GeoportalStationMapItem {
  station_id: string;
  station_code: string;
  station_name: string;
  status: StationStatus;
  latitude: number;
  longitude: number;
  zone_id: string;
  zone_name: string;
  zone_color: string;
  device_status: DeviceStatus | null;
  open_alerts_count: number;
  is_live: boolean;
  visitas_total: number;
  visitas_identificadas: number;
  visitas_sin_identificar: number;
}

/** Backward-compat alias */
export type GeoportalStationRead = GeoportalStationMapItem;

/** Full detail — fetched on-demand when a station is selected. */
export interface GeoportalStationDetail extends GeoportalStationMapItem {
  food_type: string | null;
  device: GeoportalDeviceInfo | null;
  latest_telemetry: GeoportalTelemetry | null;
  peso_promedio_g: number | null;
  peso_mediana_g: number | null;
  visitas_por_dia: number[];
  recent_events: GeoportalRecentEvent[];
}

// ── GEO-4 ────────────────────────────────────────────────────────────────────

export type ActivityItemType =
  | "feeding"
  | "rfid_read"
  | "photo"
  | "alert"
  | "telemetry";

export interface ActivityItem {
  item_type: ActivityItemType;
  timestamp: string;
  description: string;
  rfid_tag: string | null;
  animal_species: string | null;
  media_urls: string[];
  severity: string | null;
}

export interface GeoportalAnimalRead {
  animal_id: string;
  rfid_tag: string;
  species: string;
  sex: string;
  estimated_age: string | null;
  notes: string | null;
  registered_at: string;
  total_visits: number;
  last_visit: string | null;
  avg_consumed_g: number | null;
}

// ── GEO-5 ─────────────────────────────────────────────────────────────────────

export interface StationStatRow {
  station_id: string;
  station_code: string;
  station_name: string;
  zone_id: string;
  zone_name: string;
  zone_color: string;
  visitas: number;
  identificados: number;
  sin_identificar: number;
  peso_promedio_g: number | null;
  status: import("@/api/types/enums").StationStatus;
  open_alerts: number;
}

export interface SectorStatRow {
  zone_id: string;
  zone_name: string;
  zone_color: string;
  num_estaciones: number;
  visitas: number;
  identificados: number;
  sin_identificar: number;
  pct_sin_id: number;
  peso_promedio_g: number | null;
  en_alerta: number;
}

export interface AnimalMovement {
  animal_id: string;
  rfid_tag: string;
  species: string;
  sex: string;
  distinct_stations: number;
  path: string[];
  path_names: string[];
}

export interface GeoportalStatsResponse {
  time_filter: string;
  total_estaciones: number;
  total_sectores: number;
  total_animales_con_chip: number;
  total_visitas: number;
  avistamientos_sin_chip: number;
  estaciones: StationStatRow[];
  sectores: SectorStatRow[];
  animales_con_chip: AnimalMovement[];
}

// ── GEO-7 ─────────────────────────────────────────────────────────────────────

export type EventFilter = "all" | "identified" | "unidentified";

export interface StationEventDetail {
  event_id: string;
  timestamp: string;
  rfid_tag: string | null;
  animal_id: string | null;
  animal_species: string | null;
  animal_sex: string | null;
  consumed_g: number | null;
  temperature_c: number | null;
  humidity_pct: number | null;
  media_urls: string[];
  is_identified: boolean;
}

export interface StationEventsResponse {
  station_id: string;
  station_name: string;
  total: number;
  identificadas: number;
  sin_identificar: number;
  page: number;
  pages: number;
  events: StationEventDetail[];
}

// ── GEO-9 ─────────────────────────────────────────────────────────────────────

export type DarwinCoreSourceStatus = "ok" | "fuzzy_match" | "not_found" | "unavailable";

export interface GbifTaxonomy {
  kingdom: string | null;
  phylum: string | null;
  taxon_class: string | null;
  order: string | null;
  family: string | null;
  genus: string | null;
  specific_epithet: string | null;
  scientific_name: string | null;
  scientific_name_authorship: string | null;
  taxon_rank: string | null;
  vernacular_name: string | null;
  gbif_usage_key: number | null;
  gbif_confidence: number | null;
  gbif_match_type: string | null;
}

export interface DarwinCoreObservation {
  occurrence_id: string;
  catalog_number: string | null;
  basis_of_record: string;
  event_date: string | null;
  recorded_by: string;
  sex: string | null;
  life_stage: string | null;
  occurrence_remarks: string | null;
  individual_count: number;
  decimal_latitude: number | null;
  decimal_longitude: number | null;
  geodetic_datum: string;
  coordinate_uncertainty_in_meters: number;
  country: string | null;
  state_province: string | null;
  municipality: string | null;
  locality: string | null;
  location_remarks: string | null;
  institution_code: string;
  collection_code: string;
  dataset_name: string;
  rights_holder: string;
  license: string;
  nomenclatural_code: string;
}

export interface DarwinCoreSources {
  taxonomy: {
    provider: string;
    url: string | null;
    api_url: string | null;
    license: string;
  };
  observation: {
    provider: string;
    platform: string;
  };
}

export interface DarwinCoreResponse {
  animal_id: string;
  species: string;
  source_status: DarwinCoreSourceStatus;
  taxonomy: GbifTaxonomy | null;
  observation: DarwinCoreObservation;
  sources: DarwinCoreSources;
  generated_at: string;
}

// ── GEO-6 ─────────────────────────────────────────────────────────────────────

export interface FeedingEvent {
  event_id: string;
  station_id: string;
  station_name: string;
  timestamp: string;
  consumed_g: number | null;
  temperature_c: number | null;
  humidity_pct: number | null;
  media_urls: string[];
}

export interface FeederRankItem {
  station_id: string;
  station_name: string;
  visits: number;
  pct: number;
  is_primary: boolean;
}

export interface TraceStop {
  station_id: string;
  station_name: string;
  lat: number;
  lng: number;
  timestamp: string;
}

export interface AnimalHistoryResponse {
  animal_id: string;
  rfid_tag: string;
  species: string;
  sex: string;
  estimated_age: string | null;
  notes: string | null;
  total_alimentaciones: number;
  total_estaciones: number;
  dias_activo: number;
  peso_promedio_g: number | null;
  actividad_semanal: number[];
  feeder_ranking: FeederRankItem[];
  timeline: FeedingEvent[];
  trace_path: TraceStop[];
  insight_text: string;
  time_filter: string;
}
