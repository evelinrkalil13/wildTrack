import { useQuery } from "@tanstack/react-query";
import { getStationEvents } from "../api/geoportal.api";
import type { EventFilter, StationEventsResponse, TimePeriod } from "../api/geoportal.types";

export function useStationEvents(
  stationId: string | null,
  page: number,
  filter: EventFilter,
  timePeriod: TimePeriod
) {
  return useQuery<StationEventsResponse>({
    queryKey: ["geoportal", "station-events", stationId, page, filter, timePeriod],
    queryFn: () => getStationEvents(stationId!, page, filter, timePeriod),
    enabled: !!stationId,
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  });
}
