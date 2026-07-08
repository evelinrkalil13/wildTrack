import { apiClient } from "@/api/client";
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserRead,
} from "./auth.types";

export const authApi = {
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>("/auth/login", data);
    return res.data;
  },

  register: async (data: RegisterRequest): Promise<UserRead> => {
    const res = await apiClient.post<UserRead>("/auth/register", data);
    return res.data;
  },

  me: async (): Promise<UserRead> => {
    const res = await apiClient.get<UserRead>("/auth/me");
    return res.data;
  },
};
