import { apiClient } from "@/api/client";
import type {
  MemberAssign,
  MemberListResponse,
  MemberRead,
  MemberUpdate,
} from "./members.types";

export async function listMembers(
  stationId: string,
  params: { page: number; page_size: number }
): Promise<MemberListResponse> {
  const res = await apiClient.get<MemberListResponse>(
    `/stations/${stationId}/members`,
    { params }
  );
  return res.data;
}

export async function assignMember(
  stationId: string,
  data: MemberAssign
): Promise<MemberRead> {
  const res = await apiClient.post<MemberRead>(
    `/stations/${stationId}/members`,
    data
  );
  return res.data;
}

export async function updateMemberRole(
  stationId: string,
  memberId: string,
  data: MemberUpdate
): Promise<MemberRead> {
  const res = await apiClient.patch<MemberRead>(
    `/stations/${stationId}/members/${memberId}`,
    data
  );
  return res.data;
}

export async function removeMember(
  stationId: string,
  memberId: string
): Promise<void> {
  await apiClient.delete(`/stations/${stationId}/members/${memberId}`);
}
