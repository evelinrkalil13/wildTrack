import { useMutation } from "@tanstack/react-query";
import {
  changePassword,
  updateProfile,
  type ChangePasswordRequest,
  type UpdateProfileRequest,
} from "../api/profile.api";

export function useUpdateProfile() {
  return useMutation({
    mutationFn: (data: UpdateProfileRequest) => updateProfile(data),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: ChangePasswordRequest) => changePassword(data),
  });
}
