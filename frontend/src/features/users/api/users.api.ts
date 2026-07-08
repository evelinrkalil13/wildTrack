import { apiClient } from "@/api/client";
import type { UserListItem, UserListResponse, UserRoleUpdateRequest } from "./users.types";

export interface ListUsersParams {
  page: number;
  page_size: number;
  search?: string;
}

export async function listUsers(params: ListUsersParams): Promise<UserListResponse> {
  const res = await apiClient.get<UserListResponse>("/users", { params });
  return res.data;
}

export async function updateUserRole(userId: string, data: UserRoleUpdateRequest): Promise<UserListItem> {
  const res = await apiClient.patch<UserListItem>(`/users/${userId}/role`, data);
  return res.data;
}
