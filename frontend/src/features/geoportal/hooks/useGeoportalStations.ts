import { useQuery } from "@tanstack/react-query";
import { getGeoportalStations } from "../api/geoportal.api";
import type { TimePeriod } from "../api/geoportal.types";

export function useGeoportalStations(timePeriod: TimePeriod = "7d") {
  return useQuery({
    queryKey: ["geoportal-stations", timePeriod],
    queryFn: () => getGeoportalStations(timePeriod),
    staleTime: 60_000,
    refetchInterval: 120_000,
    retry: false,
  });
}
