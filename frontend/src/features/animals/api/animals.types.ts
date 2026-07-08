import type { AnimalSex } from "@/api/types/enums";

export interface AnimalRead {
  id: string;
  rfid_tag: string | null;
  species: string;
  sex: AnimalSex;
  estimated_age: string | null;
  is_identified: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnimalCreate {
  species: string;
  sex: AnimalSex;
  rfid_tag?: string;
  estimated_age?: string;
  notes?: string;
}

export interface AnimalUpdate {
  rfid_tag?: string | null;
  species?: string;
  sex?: AnimalSex;
  estimated_age?: string | null;
  notes?: string | null;
}

export interface AnimalListResponse {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: AnimalRead[];
}
