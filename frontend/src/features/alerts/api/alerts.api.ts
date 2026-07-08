import { apiClient } from "@/api/client";
import type { AlertListResponse, AlertRead } from "./alerts.types";

export interface ListAlertsParams {
  page: number;
  page_size: number;
  resolved?: boolean;
}

export async function listAlerts(params: ListAlertsParams): Promise<AlertListResponse> {
  const res = await apiClient.get<AlertListResponse>("/alerts", { params });
  return res.data;
}

export async function resolveAlert(id: string): Promise<AlertRead> {
  const res = await apiClient.patch<AlertRead>(`/alerts/${id}/resolve`);
  return res.data;
}
