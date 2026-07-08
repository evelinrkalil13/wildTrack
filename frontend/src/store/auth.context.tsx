import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { UserSummary } from "@/features/auth/api/auth.types";

const TOKEN_KEY = "wt_token";

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
}

function restoreSession(): { token: string; user: UserSummary } | null {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const raw = localStorage.getItem("wt_user");
    if (!token || !raw || isTokenExpired(token)) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem("wt_user");
      return null;
    }
    return { token, user: JSON.parse(raw) as UserSummary };
  } catch {
    return null;
  }
}

interface AuthContextValue {
  user: UserSummary | null;
  token: string | null;
  isAuthenticated: boolean;
  setAuth: (token: string, user: UserSummary) => void;
  clearAuth: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [{ token, user }, setSession] = useState<{
    token: string | null;
    user: UserSummary | null;
  }>(() => {
    const s = restoreSession();
    return { token: s?.token ?? null, user: s?.user ?? null };
  });

  const setAuth = useCallback((newToken: string, newUser: UserSummary) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    localStorage.setItem("wt_user", JSON.stringify(newUser));
    setSession({ token: newToken, user: newUser });
  }, []);

  const clearAuth = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("wt_user");
    setSession({ token: null, user: null });
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, token, isAuthenticated: !!token, setAuth, clearAuth }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
