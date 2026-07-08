import type { StationUserRole } from "@/api/types/enums";

export interface MemberRead {
  id: string;
  station_id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  role: StationUserRole;
  created_at: string;
}

export interface MemberAssign {
  user_id: string;
  role: StationUserRole;
}

export interface MemberUpdate {
  role: StationUserRole;
}

export interface MemberListResponse {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: MemberRead[];
}
