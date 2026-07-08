import { useQuery } from "@tanstack/react-query";
import { listAnimals } from "../api/animals.api";
import type { AnimalSex } from "@/api/types/enums";

interface UseAnimalsParams {
  page: number;
  pageSize: number;
  species?: string;
  sex?: AnimalSex;
  isIdentified?: boolean;
}

export function useAnimals({ page, pageSize, species, sex, isIdentified }: UseAnimalsParams) {
  return useQuery({
    queryKey: ["animals", page, pageSize, species, sex, isIdentified],
    queryFn: () =>
      listAnimals({
        page,
        page_size: pageSize,
        species: species || undefined,
        sex: sex || undefined,
        is_identified: isIdentified,
      }),
    staleTime: 30_000,
  });
}
