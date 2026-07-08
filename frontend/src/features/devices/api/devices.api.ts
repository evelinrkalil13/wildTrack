import { apiClient } from "@/api/client";
import type { DeviceStatus } from "@/api/types/enums";
import type {
  DeviceAssign,
  DeviceAssignRead,
  DeviceCreate,
  DeviceListResponse,
  DeviceRead,
  DeviceUpdate,
} from "./devices.types";

export interface ListDevicesParams {
  page: number;
  page_size: number;
  status?: DeviceStatus;
}

export async function listDevices(params: ListDevicesParams): Promise<DeviceListResponse> {
  const res = await apiClient.get<DeviceListResponse>("/devices", { params });
  return res.data;
}

export async function createDevice(data: DeviceCreate): Promise<DeviceRead> {
  const res = await apiClient.post<DeviceRead>("/devices", data);
  return res.data;
}

export async function updateDevice(id: string, data: DeviceUpdate): Promise<DeviceRead> {
  const res = await apiClient.patch<DeviceRead>(`/devices/${id}`, data);
  return res.data;
}

export async function deleteDevice(id: string): Promise<void> {
  await apiClient.delete(`/devices/${id}`);
}

export async function assignDevice(id: string, data: DeviceAssign): Promise<DeviceAssignRead> {
  const res = await apiClient.patch<DeviceAssignRead>(`/devices/${id}/assign`, data);
  return res.data;
}

export async function unassignDevice(id: string): Promise<DeviceAssignRead> {
  const res = await apiClient.patch<DeviceAssignRead>(`/devices/${id}/unassign`);
  return res.data;
}
