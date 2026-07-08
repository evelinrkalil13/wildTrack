import { apiClient } from "@/api/client";
import type { StationCreate, StationListResponse, StationRead, StationUpdate } from "./stations.types";
import type { StationStatus } from "@/api/types/enums";

export interface ListStationsParams {
  page: number;
  page_size: number;
  status?: StationStatus;
}

export async function listStations(params: ListStationsParams): Promise<StationListResponse> {
  const res = await apiClient.get<StationListResponse>("/stations", { params });
  return res.data;
}

export async function createStation(data: StationCreate): Promise<StationRead> {
  const res = await apiClient.post<StationRead>("/stations", data);
  return res.data;
}

export async function updateStation(id: string, data: StationUpdate): Promise<StationRead> {
  const res = await apiClient.patch<StationRead>(`/stations/${id}`, data);
  return res.data;
}

export async function deleteStation(id: string): Promise<void> {
  await apiClient.delete(`/stations/${id}`);
}
