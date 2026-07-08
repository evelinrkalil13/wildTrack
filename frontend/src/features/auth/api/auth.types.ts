import type { UserRole } from "@/api/types/enums";

export interface UserSummary {
  id: string;
  name: string;
  email: string;
  role: UserRole;
}

export interface UserRead {
  id: string;
  name: string;
  document: string | null;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserSummary;
}

export interface RegisterRequest {
  name: string;
  document: string;
  email: string;
  password: string;
}
