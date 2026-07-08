export interface StationFoodRead {
  id: string;
  station_id: string;
  food_id: string;
  food_name: string;
  food_type: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StationFoodAdd {
  food_id: string;
  active: boolean;
}

export interface StationFoodListResponse {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: StationFoodRead[];
}
