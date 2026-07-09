import { useQuery } from "@tanstack/react-query";
import { getStationDetail } from "../api/geoportal.api";
import type { TimePeriod } from "../api/geoportal.types";

export function useStationDetail(
  stationId: string | null,
  timePeriod: TimePeriod = "7d"
) {
  return useQuery({
    queryKey: ["geoportal-station-detail", stationId, timePeriod],
    queryFn: () => getStationDetail(stationId!, timePeriod),
    enabled: stationId !== null,
    staleTime: 30_000,
    retry: false,
  });
}
