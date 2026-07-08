import { useQuery } from "@tanstack/react-query";
import { listZones } from "../api/zones.api";
import type { ZoneRead } from "../api/zones.types";

interface UseZonesParams {
  page: number;
  pageSize: number;
  country?: string;
}

export function useZones({ page, pageSize, country }: UseZonesParams) {
  return useQuery({
    queryKey: ["zones", page, pageSize, country],
    queryFn: () =>
      listZones({ page, page_size: pageSize, country: country || undefined }),
    staleTime: 30_000,
  });
}

export function useAllZones() {
  return useQuery<ZoneRead[]>({
    queryKey: ["zones", "all"],
    queryFn: async () => {
      const res = await listZones({ page: 1, page_size: 100 });
      return res.items;
    },
    staleTime: 60_000,
  });
}
