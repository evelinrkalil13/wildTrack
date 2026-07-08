import { useQuery } from "@tanstack/react-query";
import { fetchCount, fetchRecentAlerts } from "../api/dashboard.api";
import type { AlertRead } from "../api/dashboard.types";

const STALE_MS = 60_000;

export function useTotalStations() {
  return useQuery({
    queryKey: ["dashboard", "stations", "total"],
    queryFn: () => fetchCount("/stations"),
    staleTime: STALE_MS,
  });
}

export function useActiveStations() {
  return useQuery({
    queryKey: ["dashboard", "stations", "active"],
    queryFn: () => fetchCount("/stations", { status: "active" }),
    staleTime: STALE_MS,
  });
}

export function useTotalDevices() {
  return useQuery({
    queryKey: ["dashboard", "devices", "total"],
    queryFn: () => fetchCount("/devices"),
    staleTime: STALE_MS,
  });
}

export function useOnlineDevices() {
  return useQuery({
    queryKey: ["dashboard", "devices", "online"],
    queryFn: () => fetchCount("/devices", { status: "online" }),
    staleTime: STALE_MS,
  });
}

export function useTotalAnimals() {
  return useQuery({
    queryKey: ["dashboard", "animals", "total"],
    queryFn: () => fetchCount("/animals"),
    staleTime: STALE_MS,
  });
}

export function useTotalFoods() {
  return useQuery({
    queryKey: ["dashboard", "foods", "total"],
    queryFn: () => fetchCount("/foods"),
    staleTime: STALE_MS,
  });
}

export function useOpenAlerts() {
  return useQuery({
    queryKey: ["dashboard", "alerts", "open"],
    queryFn: () => fetchCount("/alerts", { resolved: false }),
    staleTime: STALE_MS,
  });
}

export function useRecentAlerts() {
  return useQuery<AlertRead[]>({
    queryKey: ["dashboard", "alerts", "recent"],
    queryFn: fetchRecentAlerts,
    staleTime: STALE_MS,
  });
}
