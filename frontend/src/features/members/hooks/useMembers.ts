import { useQuery } from "@tanstack/react-query";
import { listMembers } from "../api/members.api";

export function useMembers(
  stationId: string | null,
  page: number,
  pageSize: number
) {
  return useQuery({
    queryKey: ["members", stationId, page, pageSize],
    queryFn: () => listMembers(stationId!, { page, page_size: pageSize }),
    enabled: !!stationId,
    staleTime: 30_000,
  });
}
