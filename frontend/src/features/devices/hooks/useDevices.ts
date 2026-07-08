import { useQuery } from "@tanstack/react-query";
import { listDevices } from "../api/devices.api";
import type { DeviceStatus } from "@/api/types/enums";

interface UseDevicesParams {
  page: number;
  pageSize: number;
  status?: DeviceStatus;
}

export function useDevices({ page, pageSize, status }: UseDevicesParams) {
  return useQuery({
    queryKey: ["devices", page, pageSize, status],
    queryFn: () =>
      listDevices({ page, page_size: pageSize, status: status || undefined }),
    staleTime: 30_000,
  });
}
