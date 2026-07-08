import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { createAnimal, deleteAnimal, updateAnimal } from "../api/animals.api";
import type { AnimalCreate, AnimalUpdate } from "../api/animals.types";

function invalidateAll(qc: QueryClient) {
  qc.invalidateQueries({ queryKey: ["animals"] });
  qc.invalidateQueries({ queryKey: ["dashboard"] });
}

export function useCreateAnimal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AnimalCreate) => createAnimal(data),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateAnimal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AnimalUpdate }) => updateAnimal(id, data),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteAnimal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteAnimal(id),
    onSuccess: () => invalidateAll(qc),
  });
}
