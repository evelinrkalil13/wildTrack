import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/store/auth.context";
import type { UserRole } from "@/api/types/enums";
import ForbiddenPage from "@/pages/ForbiddenPage";

export function RequireAuth() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/auth/login"
        state={{ returnTo: location.pathname }}
        replace
      />
    );
  }

  return <Outlet />;
}

interface RequireRoleProps {
  roles: UserRole[];
}

export function RequireRole({ roles }: RequireRoleProps) {
  const { user } = useAuth();

  if (!user || !roles.includes(user.role as UserRole)) {
    return <ForbiddenPage />;
  }

  return <Outlet />;
}
