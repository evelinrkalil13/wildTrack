import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createZone, deleteZone, updateZone } from "../api/zones.api";
import type { ZoneCreate, ZoneUpdate } from "../api/zones.types";

export function useCreateZone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ZoneCreate) => createZone(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["zones"] }),
  });
}

export function useUpdateZone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ZoneUpdate }) =>
      updateZone(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["zones"] }),
  });
}

export function useDeleteZone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteZone(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["zones"] }),
  });
}
