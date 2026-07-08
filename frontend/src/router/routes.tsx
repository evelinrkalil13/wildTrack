import { createBrowserRouter, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import { CircularProgress, Box } from "@mui/material";
import AuthLayout from "@/layouts/AuthLayout";
import AppLayout from "@/layouts/AppLayout";
import { RequireAuth, RequireRole } from "./guards";
import { UserRole } from "@/api/types/enums";
import NotFoundPage from "@/pages/NotFoundPage";

// Lazy page imports
const LoginPage = lazy(() => import("@/features/auth/pages/LoginPage"));
const RegisterPage = lazy(() => import("@/features/auth/pages/RegisterPage"));
const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const ZonesPage = lazy(() => import("@/features/zones/pages/ZonesPage"));
const StationsPage = lazy(() => import("@/features/stations/pages/StationsPage"));
const DevicesPage = lazy(() => import("@/features/devices/pages/DevicesPage"));
const AnimalsPage = lazy(() => import("@/features/animals/pages/AnimalsPage"));
const FoodsPage   = lazy(() => import("@/features/foods/pages/FoodsPage"));
const AlertsPage  = lazy(() => import("@/features/alerts/pages/AlertsPage"));
const PlaceholderPage = lazy(() => import("@/pages/PlaceholderPage"));

function PageLoader() {
  return (
    <Box
      sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh" }}
    >
      <CircularProgress color="primary" />
    </Box>
  );
}

function wrap(element: React.ReactNode) {
  return <Suspense fallback={<PageLoader />}>{element}</Suspense>;
}

export const router = createBrowserRouter([
  // Root redirect
  { index: true, element: <Navigate to="/app/dashboard" replace /> },

  // Auth routes — no guard, no sidebar
  {
    element: <AuthLayout />,
    children: [
      {
        path: "/auth/login",
        element: wrap(<LoginPage />),
      },
      {
        path: "/auth/register",
        element: wrap(<RegisterPage />),
      },
    ],
  },

  // Protected app routes
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            path: "/app/dashboard",
            element: wrap(<DashboardPage />),
          },
          {
            path: "/app/map",
            element: wrap(<PlaceholderPage title="Geoportal" slice="FE-6" />),
          },
          {
            path: "/app/stations",
            element: wrap(<StationsPage />),
          },
          {
            path: "/app/animals",
            element: wrap(<AnimalsPage />),
          },
          {
            path: "/app/alerts",
            element: wrap(<AlertsPage />),
          },
          {
            path: "/app/profile",
            element: wrap(<PlaceholderPage title="Mi perfil" slice="FE-7" />),
          },
          // Admin + Researcher
          {
            element: (
              <RequireRole roles={[UserRole.admin, UserRole.researcher]} />
            ),
            children: [
              {
                path: "/app/zones",
                element: wrap(<ZonesPage />),
              },
              {
                path: "/app/foods",
                element: wrap(<FoodsPage />),
              },
            ],
          },
          // Admin only
          {
            element: <RequireRole roles={[UserRole.admin]} />,
            children: [
              {
                path: "/app/devices",
                element: wrap(<DevicesPage />),
              },
              {
                path: "/app/users",
                element: wrap(<PlaceholderPage title="Usuarios" slice="FE-7" />),
              },
            ],
          },
        ],
      },
    ],
  },

  // 404
  { path: "*", element: <NotFoundPage /> },
]);
