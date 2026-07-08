import { useQuery } from "@tanstack/react-query";
import { listFoods } from "../api/foods.api";

interface UseFoodsParams {
  page: number;
  pageSize: number;
}

export function useFoods({ page, pageSize }: UseFoodsParams) {
  return useQuery({
    queryKey: ["foods", page, pageSize],
    queryFn: () => listFoods({ page, page_size: pageSize }),
    staleTime: 30_000,
  });
}
