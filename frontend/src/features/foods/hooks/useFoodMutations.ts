import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { createFood, deleteFood, updateFood } from "../api/foods.api";
import type { FoodCreate, FoodUpdate } from "../api/foods.types";

function invalidateAll(qc: QueryClient) {
  qc.invalidateQueries({ queryKey: ["foods"] });
  qc.invalidateQueries({ queryKey: ["dashboard"] });
}

export function useCreateFood() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: FoodCreate) => createFood(data),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateFood() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: FoodUpdate }) => updateFood(id, data),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteFood() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteFood(id),
    onSuccess: () => invalidateAll(qc),
  });
}
