import type { UserRole } from "@/api/types/enums";

export interface UserListItem {
  id: string;
  name: string;
  email: string;
  role: UserRole;
}

export interface UserListResponse {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: UserListItem[];
}

export interface UserRoleUpdateRequest {
  role: UserRole;
}
