export enum AlertType {
  rfid_read_failure = "rfid_read_failure",
  connectivity_lost = "connectivity_lost",
  sensor_failure = "sensor_failure",
  inactive_station = "inactive_station",
  empty_tank = "empty_tank",
  camera_failure = "camera_failure",
}

export interface AlertRead {
  alert_id: string;
  alert_type: AlertType;
  station_id: string | null;
  device_id: string | null;
  event_id: string | null;
  message: string;
  resolved: boolean;
  resolved_at: string | null;
  created_at: string;
}

export interface AlertListResponse {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: AlertRead[];
}

export interface LatestTelemetryRead {
  timestamp: string;
  temperature_c: number | null;
  humidity_pct: number | null;
  wifi_rssi_dbm: number | null;
  battery_pct: number | null;
  firmware_version: string | null;
  station_id: string | null;
  device_id: string | null;
}
