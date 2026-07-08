import { apiClient } from "@/api/client";
import type { UserListResponse } from "./users.types";

export interface ListUsersParams {
  page: number;
  page_size: number;
  search?: string;
}

export async function listUsers(params: ListUsersParams): Promise<UserListResponse> {
  const res = await apiClient.get<UserListResponse>("/users", { params });
  return res.data;
}
