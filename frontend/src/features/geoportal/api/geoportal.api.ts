import { apiClient } from "@/api/client";
import type { GeoportalStationRead } from "./geoportal.types";

export async function getGeoportalStations(): Promise<GeoportalStationRead[]> {
  const res = await apiClient.get<GeoportalStationRead[]>("/geoportal/stations");
  return res.data;
}
