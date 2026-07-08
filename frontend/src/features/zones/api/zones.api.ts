import { apiClient } from "@/api/client";
import type { ZoneCreate, ZoneListResponse, ZoneRead, ZoneUpdate } from "./zones.types";

export interface ListZonesParams {
  page: number;
  page_size: number;
  country?: string;
}

export async function listZones(params: ListZonesParams): Promise<ZoneListResponse> {
  const res = await apiClient.get<ZoneListResponse>("/zones", { params });
  return res.data;
}

export async function createZone(data: ZoneCreate): Promise<ZoneRead> {
  const res = await apiClient.post<ZoneRead>("/zones", data);
  return res.data;
}

export async function updateZone(id: string, data: ZoneUpdate): Promise<ZoneRead> {
  const res = await apiClient.patch<ZoneRead>(`/zones/${id}`, data);
  return res.data;
}

export async function deleteZone(id: string): Promise<void> {
  await apiClient.delete(`/zones/${id}`);
}
