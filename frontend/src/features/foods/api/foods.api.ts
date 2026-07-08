import { apiClient } from "@/api/client";
import type {
  FoodCreate,
  FoodListResponse,
  FoodRead,
  FoodStationListResponse,
  FoodUpdate,
} from "./foods.types";

export interface ListFoodsParams {
  page: number;
  page_size: number;
}

export async function listFoods(params: ListFoodsParams): Promise<FoodListResponse> {
  const res = await apiClient.get<FoodListResponse>("/foods", { params });
  return res.data;
}

export async function createFood(data: FoodCreate): Promise<FoodRead> {
  const res = await apiClient.post<FoodRead>("/foods", data);
  return res.data;
}

export async function updateFood(id: string, data: FoodUpdate): Promise<FoodRead> {
  const res = await apiClient.patch<FoodRead>(`/foods/${id}`, data);
  return res.data;
}

export async function deleteFood(id: string): Promise<void> {
  await apiClient.delete(`/foods/${id}`);
}

export async function getFoodStations(foodId: string): Promise<FoodStationListResponse> {
  const res = await apiClient.get<FoodStationListResponse>(`/foods/${foodId}/stations`);
  return res.data;
}
