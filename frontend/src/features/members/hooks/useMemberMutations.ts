import { useMutation, useQueryClient } from "@tanstack/react-query";
import { assignMember, removeMember, updateMemberRole } from "../api/members.api";
import type { MemberAssign, MemberUpdate } from "../api/members.types";

function invalidate(qc: ReturnType<typeof useQueryClient>, stationId: string) {
  qc.invalidateQueries({ queryKey: ["members", stationId] });
}

export function useAssignMember(stationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MemberAssign) => assignMember(stationId, data),
    onSuccess: () => invalidate(qc, stationId),
  });
}

export function useUpdateMemberRole(stationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ memberId, data }: { memberId: string; data: MemberUpdate }) =>
      updateMemberRole(stationId, memberId, data),
    onSuccess: () => invalidate(qc, stationId),
  });
}

export function useRemoveMember(stationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (memberId: string) => removeMember(stationId, memberId),
    onSuccess: () => invalidate(qc, stationId),
  });
}
