import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateUserRole } from "../api/users.api";
import type { UserRoleUpdateRequest } from "../api/users.types";

export function useUpdateUserRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UserRoleUpdateRequest }) =>
      updateUserRole(userId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}
