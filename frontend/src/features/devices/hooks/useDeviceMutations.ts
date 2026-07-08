import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import {
  assignDevice,
  createDevice,
  deleteDevice,
  unassignDevice,
  updateDevice,
} from "../api/devices.api";
import type { DeviceAssign, DeviceCreate, DeviceUpdate } from "../api/devices.types";

function invalidateAll(qc: QueryClient) {
  qc.invalidateQueries({ queryKey: ["devices"] });
  qc.invalidateQueries({ queryKey: ["dashboard"] });
}

export function useCreateDevice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DeviceCreate) => createDevice(data),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateDevice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DeviceUpdate }) =>
      updateDevice(id, data),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteDevice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDevice(id),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAssignDevice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DeviceAssign }) =>
      assignDevice(id, data),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUnassignDevice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => unassignDevice(id),
    onSuccess: () => invalidateAll(qc),
  });
}
