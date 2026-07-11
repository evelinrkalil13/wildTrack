import { apiClient } from "@/api/client";
import type { AlertListResponse, AlertRead, LatestTelemetryRead } from "./dashboard.types";

export async function fetchCount(
  path: string,
  params?: Record<string, string | number | boolean>,
): Promise<number> {
  const res = await apiClient.get<{ total: number }>(path, {
    params: { page: 1, page_size: 1, ...params },
  });
  return res.data.total;
}

export async function fetchRecentAlerts(): Promise<AlertRead[]> {
  const res = await apiClient.get<AlertListResponse>("/alerts", {
    params: { resolved: false, page: 1, page_size: 5 },
  });
  return res.data.items;
}

export async function fetchLatestTelemetry(): Promise<LatestTelemetryRead> {
  const res = await apiClient.get<LatestTelemetryRead>("/geoportal/telemetry/latest");
  return res.data;
}
