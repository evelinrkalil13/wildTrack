import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  activateStationFood,
  addFoodToStation,
  deactivateStationFood,
  removeStationFood,
} from "../api/station_foods.api";
import type { StationFoodAdd } from "../api/station_foods.types";

function invalidate(qc: ReturnType<typeof useQueryClient>, stationId: string) {
  qc.invalidateQueries({ queryKey: ["station-foods", stationId] });
  qc.invalidateQueries({ queryKey: ["foods"] });
}

export function useAddFoodToStation(stationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: StationFoodAdd) => addFoodToStation(stationId, data),
    onSuccess: () => invalidate(qc, stationId),
  });
}

export function useActivateStationFood(stationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sfId: string) => activateStationFood(stationId, sfId),
    onSuccess: () => invalidate(qc, stationId),
  });
}

export function useDeactivateStationFood(stationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sfId: string) => deactivateStationFood(stationId, sfId),
    onSuccess: () => invalidate(qc, stationId),
  });
}

export function useRemoveStationFood(stationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sfId: string) => removeStationFood(stationId, sfId),
    onSuccess: () => invalidate(qc, stationId),
  });
}
