import { useQuery } from "@tanstack/react-query";
import { getGeoportalStats } from "../api/geoportal.api";
import type { TimePeriod } from "../api/geoportal.types";

export function useGeoportalStats(timePeriod: TimePeriod = "7d") {
  return useQuery({
    queryKey: ["geoportal-stats", timePeriod],
    queryFn: () => getGeoportalStats(timePeriod),
    staleTime: 120_000,
    retry: false,
  });
}
