export interface FoodRead {
  id: string;
  name: string;
  type: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface FoodCreate {
  name: string;
  type: string;
  description?: string;
}

export interface FoodUpdate {
  name?: string;
  type?: string;
  description?: string | null;
}

export interface FoodListResponse {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: FoodRead[];
}

export interface FoodStationRead {
  station_id: string;
  station_code: string;
  station_name: string;
  active: boolean;
  created_at: string;
}

export interface FoodStationListResponse {
  total: number;
  items: FoodStationRead[];
}
