import { apiClient } from "@/api/client";
import type { StationFoodAdd, StationFoodListResponse, StationFoodRead } from "./station_foods.types";

export async function listStationFoods(
  stationId: string,
  params: { page: number; page_size: number }
): Promise<StationFoodListResponse> {
  const res = await apiClient.get<StationFoodListResponse>(
    `/stations/${stationId}/foods`,
    { params }
  );
  return res.data;
}

export async function addFoodToStation(
  stationId: string,
  data: StationFoodAdd
): Promise<StationFoodRead> {
  const res = await apiClient.post<StationFoodRead>(`/stations/${stationId}/foods`, data);
  return res.data;
}

export async function activateStationFood(
  stationId: string,
  sfId: string
): Promise<StationFoodRead> {
  const res = await apiClient.patch<StationFoodRead>(
    `/stations/${stationId}/foods/${sfId}/activate`
  );
  return res.data;
}

export async function deactivateStationFood(
  stationId: string,
  sfId: string
): Promise<StationFoodRead> {
  const res = await apiClient.patch<StationFoodRead>(
    `/stations/${stationId}/foods/${sfId}/deactivate`
  );
  return res.data;
}

export async function removeStationFood(stationId: string, sfId: string): Promise<void> {
  await apiClient.delete(`/stations/${stationId}/foods/${sfId}`);
}
