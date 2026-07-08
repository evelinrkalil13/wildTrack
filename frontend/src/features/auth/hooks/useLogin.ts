import { useMutation } from "@tanstack/react-query";
import { authApi } from "../api/auth.api";
import { useAuth } from "@/store/auth.context";

export function useLogin() {
  const { setAuth } = useAuth();

  return useMutation({
    mutationFn: authApi.login,
    onSuccess: (data) => {
      setAuth(data.access_token, data.user);
    },
  });
}
