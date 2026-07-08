import { useQuery } from "@tanstack/react-query";
import { listUsers } from "../api/users.api";
import type { UserListItem } from "../api/users.types";

export function useAllUsers() {
  return useQuery<UserListItem[]>({
    queryKey: ["users", "all"],
    queryFn: async () => {
      const res = await listUsers({ page: 1, page_size: 100 });
      return res.items;
    },
    staleTime: 60_000,
  });
}
