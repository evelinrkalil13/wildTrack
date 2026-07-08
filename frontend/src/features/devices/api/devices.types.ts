import type { DeviceStatus } from "@/api/types/enums";

export interface DeviceRead {
  id: string;
  serial_number: string;
  name: string | null;
  mac_address: string | null;
  station_id: string | null;
  station_code: string | null;
  status: DeviceStatus;
  firmware_version: string | null;
  last_seen: string | null;
  created_at: string;
  updated_at: string;
}

export interface DeviceCreate {
  serial_number: string;
  name?: string;
  mac_address?: string;
}

export interface DeviceUpdate {
  name?: string;
}

export interface DeviceAssign {
  station_id: string;
}

export interface DeviceAssignRead {
  id: string;
  station_id: string | null;
  status: DeviceStatus;
  updated_at: string;
}

export interface DeviceListResponse {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: DeviceRead[];
}
