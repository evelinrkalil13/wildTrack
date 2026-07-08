import { apiClient } from "@/api/client";
import type { AnimalSex } from "@/api/types/enums";
import type {
  AnimalCreate,
  AnimalListResponse,
  AnimalRead,
  AnimalUpdate,
} from "./animals.types";

export interface ListAnimalsParams {
  page: number;
  page_size: number;
  species?: string;
  sex?: AnimalSex;
  is_identified?: boolean;
}

export async function listAnimals(params: ListAnimalsParams): Promise<AnimalListResponse> {
  const res = await apiClient.get<AnimalListResponse>("/animals", { params });
  return res.data;
}

export async function createAnimal(data: AnimalCreate): Promise<AnimalRead> {
  const res = await apiClient.post<AnimalRead>("/animals", data);
  return res.data;
}

export async function updateAnimal(id: string, data: AnimalUpdate): Promise<AnimalRead> {
  const res = await apiClient.patch<AnimalRead>(`/animals/${id}`, data);
  return res.data;
}

export async function deleteAnimal(id: string): Promise<void> {
  await apiClient.delete(`/animals/${id}`);
}
