export interface ZoneRead {
  id: string;
  name: string;
  municipality: string | null;
  city: string;
  country: string;
  altitude: number | null;
  latitude: number;
  longitude: number;
  created_at: string;
  updated_at: string;
}

export interface ZoneCreate {
  name: string;
  city: string;
  country: string;
  municipality?: string;
  altitude?: number;
  latitude: number;
  longitude: number;
}

export interface ZoneUpdate {
  name?: string;
  municipality?: string;
  city?: string;
  country?: string;
  altitude?: number;
  latitude?: number;
  longitude?: number;
}

export interface ZoneListResponse {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: ZoneRead[];
}
