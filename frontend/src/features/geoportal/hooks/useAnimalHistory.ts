import { useQuery } from "@tanstack/react-query";
import { getAnimalHistory } from "../api/geoportal.api";
import type { AnimalHistoryResponse, TimePeriod } from "../api/geoportal.types";

export function useAnimalHistory(animalId: string | null, timePeriod: TimePeriod = "all") {
  return useQuery<AnimalHistoryResponse>({
    queryKey: ["geoportal", "animal-history", animalId, timePeriod],
    queryFn: () => getAnimalHistory(animalId!, timePeriod),
    enabled: !!animalId,
    staleTime: 60_000,
  });
}
