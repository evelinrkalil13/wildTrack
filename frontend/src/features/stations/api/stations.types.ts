import type { StationStatus } from "@/api/types/enums";

export interface StationRead {
  id: string;
  code: string;
  name: string;
  zone_id: string;
  latitude: number;
  longitude: number;
  status: StationStatus;
  created_at: string;
  updated_at: string;
}

export interface StationCreate {
  code: string;
  name: string;
  zone_id: string;
  latitude: number;
  longitude: number;
}

export interface StationUpdate {
  name?: string;
  status?: StationStatus;
  zone_id?: string;
  latitude?: number;
  longitude?: number;
}

export interface StationListResponse {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: StationRead[];
}
