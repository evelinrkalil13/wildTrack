import { useQuery } from "@tanstack/react-query";
import { getDarwinCore } from "../api/geoportal.api";

export function useDarwinCore(animalId: string | null) {
  return useQuery({
    queryKey: ["darwin-core", animalId],
    queryFn: () => getDarwinCore(animalId!),
    enabled: !!animalId,
    staleTime: 1000 * 60 * 60 * 24, // 24 h — matches backend cache TTL
    retry: false,
  });
}
