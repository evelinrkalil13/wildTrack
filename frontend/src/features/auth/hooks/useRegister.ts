import { useMutation } from "@tanstack/react-query";
import { authApi } from "../api/auth.api";

export function useRegister() {
  return useMutation({ mutationFn: authApi.register });
}
