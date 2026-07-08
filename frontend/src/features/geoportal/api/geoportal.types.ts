import type { DeviceStatus, StationStatus } from "@/api/types/enums";

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

export interface GeoportalStationRead {
  station_id: string;
  station_code: string;
  station_name: string;
  status: StationStatus;
  latitude: number;
  longitude: number;
  zone_id: string;
  zone_name: string;
  device: GeoportalDeviceInfo | null;
  latest_telemetry: GeoportalTelemetry | null;
  recent_events: GeoportalRecentEvent[];
  open_alerts_count: number;
}
