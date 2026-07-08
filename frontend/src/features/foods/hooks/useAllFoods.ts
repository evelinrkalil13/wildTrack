import { useQuery } from "@tanstack/react-query";
import { listFoods } from "../api/foods.api";

export function useAllFoods() {
  return useQuery({
    queryKey: ["foods", "all"],
    queryFn: () => listFoods({ page: 1, page_size: 100 }),
    staleTime: 60_000,
    select: (data) => data.items,
  });
}
