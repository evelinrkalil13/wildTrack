import { renderHook, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "./auth.context";
import { UserRole } from "@/api/types/enums";
import type { UserSummary } from "@/features/auth/api/auth.types";

const mockUser: UserSummary = {
  id: "test-id-1",
  name: "Test User",
  email: "test@wildtrack.dev",
  role: UserRole.researcher,
};

beforeEach(() => {
  localStorage.clear();
});

describe("AuthContext", () => {
  it("starts unauthenticated when no token in storage", () => {
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
  });

  it("setAuth persists token and user", () => {
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    act(() => {
      result.current.setAuth("fake-jwt-token", mockUser);
    });
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.name).toBe("Test User");
    expect(result.current.user?.role).toBe(UserRole.researcher);
    expect(localStorage.getItem("wt_token")).toBe("fake-jwt-token");
  });

  it("clearAuth removes session from state and storage", () => {
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    act(() => {
      result.current.setAuth("fake-jwt-token", mockUser);
    });
    act(() => {
      result.current.clearAuth();
    });
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(localStorage.getItem("wt_token")).toBeNull();
  });

  it("throws when used outside AuthProvider", () => {
    // Suppress React error boundary noise in test output
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => renderHook(() => useAuth())).toThrow(
      "useAuth must be used inside <AuthProvider>"
    );
    spy.mockRestore();
  });
});
