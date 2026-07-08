import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  Box,
  AppBar,
  Toolbar,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  IconButton,
  Avatar,
  Menu,
  MenuItem,
  Divider,
  Tooltip,
} from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";
import MapIcon from "@mui/icons-material/Map";
import CellTowerIcon from "@mui/icons-material/CellTower";
import PetsIcon from "@mui/icons-material/Pets";
import NotificationsIcon from "@mui/icons-material/Notifications";
import DevicesIcon from "@mui/icons-material/Devices";
import TerrainIcon from "@mui/icons-material/Terrain";
import GrassIcon from "@mui/icons-material/Grass";
import PeopleIcon from "@mui/icons-material/People";
import LogoutIcon from "@mui/icons-material/Logout";
import PersonIcon from "@mui/icons-material/Person";
import { useAuth } from "@/store/auth.context";
import { UserRole } from "@/api/types/enums";

const DRAWER_WIDTH = 260;

interface NavItem {
  label: string;
  icon: React.ReactNode;
  path: string;
  roles?: UserRole[];
}

const NAV_ITEMS: (NavItem | "divider")[] = [
  { label: "Dashboard", icon: <DashboardIcon fontSize="small" />, path: "/app/dashboard" },
  { label: "Geoportal", icon: <MapIcon fontSize="small" />, path: "/app/map" },
  "divider",
  { label: "Estaciones", icon: <CellTowerIcon fontSize="small" />, path: "/app/stations" },
  { label: "Animales", icon: <PetsIcon fontSize="small" />, path: "/app/animals" },
  { label: "Alertas", icon: <NotificationsIcon fontSize="small" />, path: "/app/alerts" },
  "divider",
  {
    label: "Dispositivos",
    icon: <DevicesIcon fontSize="small" />,
    path: "/app/devices",
    roles: [UserRole.admin],
  },
  {
    label: "Zonas",
    icon: <TerrainIcon fontSize="small" />,
    path: "/app/zones",
    roles: [UserRole.admin, UserRole.researcher],
  },
  {
    label: "Alimentos",
    icon: <GrassIcon fontSize="small" />,
    path: "/app/foods",
    roles: [UserRole.admin, UserRole.researcher],
  },
  {
    label: "Usuarios",
    icon: <PeopleIcon fontSize="small" />,
    path: "/app/users",
    roles: [UserRole.admin],
  },
];

export default function AppLayout() {
  const { user, clearAuth } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  function handleLogout() {
    setAnchorEl(null);
    clearAuth();
    navigate("/auth/login", { replace: true });
  }

  const visibleItems = NAV_ITEMS.filter((item) => {
    if (item === "divider") return true;
    if (!item.roles) return true;
    return user && item.roles.includes(user.role as UserRole);
  });

  const initials = user?.name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase() ?? "?";

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      {/* Top Navigation Bar */}
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar sx={{ gap: 1 }}>
          {/* Brand */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                bgcolor: "secondary.main",
                boxShadow: "0 0 8px",
              }}
            />
            <Typography
              variant="h6"
              sx={{ fontFamily: "Space Grotesk", fontWeight: 700 }}
            >
              WildTrack
            </Typography>
          </Box>

          <Box sx={{ flexGrow: 1 }} />

          {/* User avatar + menu */}
          <Tooltip title={user?.name ?? ""}>
            <IconButton
              onClick={(e) => setAnchorEl(e.currentTarget)}
              size="small"
            >
              <Avatar
                sx={{
                  width: 34,
                  height: 34,
                  bgcolor: "primary.dark",
                  fontSize: "0.8rem",
                  fontWeight: 700,
                  fontFamily: "Space Grotesk",
                }}
              >
                {initials}
              </Avatar>
            </IconButton>
          </Tooltip>

          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={() => setAnchorEl(null)}
            transformOrigin={{ horizontal: "right", vertical: "top" }}
            anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
            PaperProps={{
              sx: { minWidth: 200, mt: 0.5 },
            }}
          >
            <Box sx={{ px: 2, py: 1.5 }}>
              <Typography variant="body2" fontWeight={600}>
                {user?.name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {user?.email}
              </Typography>
            </Box>
            <Divider />
            <MenuItem
              onClick={() => { setAnchorEl(null); navigate("/app/profile"); }}
              sx={{ gap: 1.5 }}
            >
              <PersonIcon fontSize="small" />
              Mi perfil
            </MenuItem>
            <MenuItem onClick={handleLogout} sx={{ gap: 1.5, color: "error.main" }}>
              <LogoutIcon fontSize="small" />
              Cerrar sesión
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {/* Sidebar Drawer */}
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: DRAWER_WIDTH,
            boxSizing: "border-box",
          },
        }}
      >
        <Toolbar /> {/* Spacer for AppBar */}

        {/* Brand in sidebar */}
        <Box
          sx={{
            px: "22px",
            py: "16px",
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ textTransform: "uppercase", letterSpacing: "0.6px" }}
          >
            Monitoreo de fauna
          </Typography>
        </Box>

        {/* Navigation */}
        <Box sx={{ overflow: "auto", flex: 1, py: 1 }}>
          <List dense disablePadding>
            {visibleItems.map((item, idx) => {
              if (item === "divider") {
                return <Divider key={idx} sx={{ my: 0.5, mx: 1 }} />;
              }

              const isActive = location.pathname.startsWith(item.path);

              return (
                <ListItemButton
                  key={item.path}
                  selected={isActive}
                  onClick={() => navigate(item.path)}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 36,
                      color: isActive ? "primary.main" : "text.secondary",
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.label}
                    primaryTypographyProps={{
                      fontSize: "0.875rem",
                      fontWeight: isActive ? 600 : 400,
                    }}
                  />
                </ListItemButton>
              );
            })}
          </List>
        </Box>

        {/* User info at bottom */}
        <Box
          sx={{
            px: 2,
            py: 1.5,
            borderTop: "1px solid",
            borderColor: "divider",
            display: "flex",
            alignItems: "center",
            gap: 1.5,
          }}
        >
          <Avatar
            sx={{
              width: 30,
              height: 30,
              bgcolor: "primary.dark",
              fontSize: "0.7rem",
              fontWeight: 700,
            }}
          >
            {initials}
          </Avatar>
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography
              variant="body2"
              fontWeight={500}
              noWrap
              sx={{ lineHeight: 1.2 }}
            >
              {user?.name}
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              noWrap
              sx={{ display: "block" }}
            >
              {user?.role?.replace("_", " ")}
            </Typography>
          </Box>
        </Box>
      </Drawer>

      {/* Main content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: "background.default",
          minHeight: "100vh",
        }}
      >
        <Toolbar /> {/* Spacer for AppBar */}
        <Outlet />
      </Box>
    </Box>
  );
}
