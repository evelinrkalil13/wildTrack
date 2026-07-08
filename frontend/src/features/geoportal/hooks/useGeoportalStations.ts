import { useQuery } from "@tanstack/react-query";
import { getGeoportalStations } from "../api/geoportal.api";

export function useGeoportalStations() {
  return useQuery({
    queryKey: ["geoportal-stations"],
    queryFn: getGeoportalStations,
    staleTime: 60_000,
    refetchInterval: 120_000,
    retry: false,
  });
}
