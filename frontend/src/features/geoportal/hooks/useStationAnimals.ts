import { useQuery } from "@tanstack/react-query";
import { getStationAnimals } from "../api/geoportal.api";
import type { TimePeriod } from "../api/geoportal.types";

export function useStationAnimals(
  stationId: string | null,
  timePeriod: TimePeriod = "7d"
) {
  return useQuery({
    queryKey: ["geoportal-station-animals", stationId, timePeriod],
    queryFn: () => getStationAnimals(stationId!, timePeriod),
    enabled: stationId !== null,
    staleTime: 60_000,
    retry: false,
  });
}
