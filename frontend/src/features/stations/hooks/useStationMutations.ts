import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createStation, deleteStation, updateStation } from "../api/stations.api";
import type { StationCreate, StationUpdate } from "../api/stations.types";

export function useCreateStation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: StationCreate) => createStation(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stations"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useUpdateStation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: StationUpdate }) =>
      updateStation(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stations"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useDeleteStation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteStation(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stations"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
