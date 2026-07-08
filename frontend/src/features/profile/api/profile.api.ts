import { apiClient } from "@/api/client";
import type { UserRead } from "@/features/auth/api/auth.types";

export interface UpdateProfileRequest {
  name: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export async function updateProfile(data: UpdateProfileRequest): Promise<UserRead> {
  const res = await apiClient.patch<UserRead>("/users/me", data);
  return res.data;
}

export async function changePassword(data: ChangePasswordRequest): Promise<void> {
  await apiClient.patch("/users/me/password", data);
}
