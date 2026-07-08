import { useQuery } from "@tanstack/react-query";
import { listStations } from "../api/stations.api";
import type { StationStatus } from "@/api/types/enums";
import type { StationRead } from "../api/stations.types";

interface UseStationsParams {
  page: number;
  pageSize: number;
  status?: StationStatus;
}

export function useStations({ page, pageSize, status }: UseStationsParams) {
  return useQuery({
    queryKey: ["stations", page, pageSize, status],
    queryFn: () =>
      listStations({ page, page_size: pageSize, status: status || undefined }),
    staleTime: 30_000,
  });
}

export function useAllStations() {
  return useQuery<StationRead[]>({
    queryKey: ["stations", "all"],
    queryFn: async () => {
      const res = await listStations({ page: 1, page_size: 100 });
      return res.items;
    },
    staleTime: 60_000,
  });
}
