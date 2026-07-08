import { useQuery } from "@tanstack/react-query";
import { listUsers } from "../api/users.api";
import type { UserListResponse } from "../api/users.types";

interface UseUsersParams {
  page: number;
  pageSize: number;
  search?: string;
}

export function useUsers({ page, pageSize, search }: UseUsersParams) {
  return useQuery<UserListResponse>({
    queryKey: ["users", page, pageSize, search],
    queryFn: () => listUsers({ page, page_size: pageSize, search }),
    staleTime: 30_000,
    retry: false,
  });
}
