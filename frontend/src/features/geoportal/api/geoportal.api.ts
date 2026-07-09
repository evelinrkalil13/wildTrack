import { apiClient } from "@/api/client";
import type {
  ActivityItem,
  AnimalHistoryResponse,
  DarwinCoreResponse,
  EventFilter,
  GeoportalAnimalRead,
  GeoportalStationDetail,
  GeoportalStationMapItem,
  GeoportalStatsResponse,
  StationEventsResponse,
  TimePeriod,
} from "./geoportal.types";

export async function getGeoportalStations(
  timePeriod: TimePeriod = "7d"
): Promise<GeoportalStationMapItem[]> {
  const res = await apiClient.get<GeoportalStationMapItem[]>(
    "/geoportal/stations",
    { params: { time_filter: timePeriod } }
  );
  return res.data;
}

export async function getStationDetail(
  stationId: string,
  timePeriod: TimePeriod = "7d"
): Promise<GeoportalStationDetail> {
  const res = await apiClient.get<GeoportalStationDetail>(
    `/geoportal/stations/${stationId}`,
    { params: { time_filter: timePeriod } }
  );
  return res.data;
}

export async function getStationAnimals(
  stationId: string,
  timePeriod: TimePeriod = "7d"
): Promise<GeoportalAnimalRead[]> {
  const res = await apiClient.get<GeoportalAnimalRead[]>(
    `/geoportal/stations/${stationId}/animals`,
    { params: { time_filter: timePeriod } }
  );
  return res.data;
}

export async function getStationActivity(
  stationId: string,
  limit = 20
): Promise<ActivityItem[]> {
  const res = await apiClient.get<ActivityItem[]>(
    `/geoportal/stations/${stationId}/activity`,
    { params: { limit } }
  );
  return res.data;
}

export async function getGeoportalStats(
  timePeriod: TimePeriod = "7d"
): Promise<GeoportalStatsResponse> {
  const res = await apiClient.get<GeoportalStatsResponse>("/geoportal/stats", {
    params: { time_filter: timePeriod },
  });
  return res.data;
}

export async function getStationEvents(
  stationId: string,
  page: number = 1,
  filter: EventFilter = "all",
  timePeriod: TimePeriod = "7d"
): Promise<StationEventsResponse> {
  const res = await apiClient.get<StationEventsResponse>(
    `/geoportal/stations/${stationId}/events`,
    { params: { page, page_size: 20, filter, time_filter: timePeriod } }
  );
  return res.data;
}

export async function getAnimalHistory(
  animalId: string,
  timePeriod: TimePeriod = "all"
): Promise<AnimalHistoryResponse> {
  const res = await apiClient.get<AnimalHistoryResponse>(
    `/geoportal/animals/${animalId}/history`,
    { params: { time_filter: timePeriod } }
  );
  return res.data;
}

export async function getDarwinCore(animalId: string): Promise<DarwinCoreResponse> {
  const res = await apiClient.get<DarwinCoreResponse>(
    `/geoportal/animals/${animalId}/darwin-core`
  );
  return res.data;
}
