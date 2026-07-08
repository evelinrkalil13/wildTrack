import { useQuery } from "@tanstack/react-query";
import { listAlerts } from "../api/alerts.api";
import type { AlertFilter } from "../api/alerts.types";

interface UseAlertsParams {
  page: number;
  pageSize: number;
  filter: AlertFilter;
}

export function useAlerts({ page, pageSize, filter }: UseAlertsParams) {
  const resolved =
    filter === "all" ? undefined : filter === "resolved" ? true : false;

  return useQuery({
    queryKey: ["alerts", page, pageSize, filter],
    queryFn: () => listAlerts({ page, page_size: pageSize, resolved }),
    staleTime: 30_000,
  });
}
