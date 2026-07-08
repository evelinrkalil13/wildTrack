import { useQuery } from "@tanstack/react-query";
import { listStationFoods } from "../api/station_foods.api";

export function useStationFoods(
  stationId: string | null,
  page: number,
  pageSize: number
) {
  return useQuery({
    queryKey: ["station-foods", stationId, page, pageSize],
    queryFn: () => listStationFoods(stationId!, { page, page_size: pageSize }),
    enabled: !!stationId,
    staleTime: 30_000,
  });
}
