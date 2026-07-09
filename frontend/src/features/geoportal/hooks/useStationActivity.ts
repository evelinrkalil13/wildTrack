import { useQuery } from "@tanstack/react-query";
import { getStationActivity } from "../api/geoportal.api";

export function useStationActivity(stationId: string | null, limit = 20) {
  return useQuery({
    queryKey: ["geoportal-station-activity", stationId, limit],
    queryFn: () => getStationActivity(stationId!, limit),
    enabled: stationId !== null,
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: false,
  });
}
