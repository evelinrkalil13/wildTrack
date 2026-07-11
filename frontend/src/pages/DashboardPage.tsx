import { Box, Grid, Typography } from "@mui/material";
import CellTowerIcon from "@mui/icons-material/CellTower";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import RouterIcon from "@mui/icons-material/Router";
import WifiIcon from "@mui/icons-material/Wifi";
import PetsIcon from "@mui/icons-material/Pets";
import GrassIcon from "@mui/icons-material/Grass";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import StatCard from "@/features/dashboard/components/StatCard";
import RecentAlerts from "@/features/dashboard/components/RecentAlerts";
import {
  useActiveStations,
  useLatestTelemetry,
  useOnlineDevices,
  useOpenAlerts,
  useTotalAnimals,
  useTotalDevices,
  useTotalFoods,
  useTotalStations,
} from "@/features/dashboard/hooks/useDashboardStats";

function formatRelativeTime(isoTimestamp: string): string {
  const diffMs = Date.now() - new Date(isoTimestamp).getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "ahora";
  if (diffMin < 60) return `${diffMin} min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH} h`;
  return `${Math.floor(diffH / 24)} días`;
}

export default function DashboardPage() {
  const totalStations = useTotalStations();
  const activeStations = useActiveStations();
  const totalDevices = useTotalDevices();
  const onlineDevices = useOnlineDevices();
  const totalAnimals = useTotalAnimals();
  const totalFoods = useTotalFoods();
  const openAlerts = useOpenAlerts();
  const latestTelemetry = useLatestTelemetry();

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
        Dashboard
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            label="Estaciones"
            sublabel="Total registradas"
            value={totalStations.data}
            icon={<CellTowerIcon fontSize="small" />}
            paletteColor="primary"
            loading={totalStations.isLoading}
            error={totalStations.isError}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            label="Estaciones activas"
            sublabel="Estado: activa"
            value={activeStations.data}
            icon={<CheckCircleIcon fontSize="small" />}
            paletteColor="success"
            loading={activeStations.isLoading}
            error={activeStations.isError}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            label="Dispositivos"
            sublabel="Total registrados"
            value={totalDevices.data}
            icon={<RouterIcon fontSize="small" />}
            paletteColor="info"
            loading={totalDevices.isLoading}
            error={totalDevices.isError}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            label="Dispositivos online"
            sublabel="Estado: online"
            value={onlineDevices.data}
            icon={<WifiIcon fontSize="small" />}
            paletteColor="success"
            loading={onlineDevices.isLoading}
            error={onlineDevices.isError}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            label="Animales"
            sublabel="Total registrados"
            value={totalAnimals.data}
            icon={<PetsIcon fontSize="small" />}
            paletteColor="warning"
            loading={totalAnimals.isLoading}
            error={totalAnimals.isError}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            label="Alimentos"
            sublabel="Tipos configurados"
            value={totalFoods.data}
            icon={<GrassIcon fontSize="small" />}
            paletteColor="secondary"
            loading={totalFoods.isLoading}
            error={totalFoods.isError}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            label="Alertas abiertas"
            sublabel="Sin resolver"
            value={openAlerts.data}
            icon={<NotificationsActiveIcon fontSize="small" />}
            paletteColor="error"
            loading={openAlerts.isLoading}
            error={openAlerts.isError}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            label="Última telemetría"
            sublabel={(() => {
              const d = latestTelemetry.data;
              if (!d) return "Sin datos";
              const parts: string[] = [];
              if (d.temperature_c != null) parts.push(`${d.temperature_c.toFixed(1)} °C`);
              if (d.humidity_pct != null) parts.push(`${d.humidity_pct.toFixed(0)} %`);
              return parts.length > 0 ? parts.join(" · ") : "Sin sensores";
            })()}
            stringValue={
              latestTelemetry.data
                ? formatRelativeTime(latestTelemetry.data.timestamp)
                : undefined
            }
            icon={<AccessTimeIcon fontSize="small" />}
            paletteColor="info"
            loading={latestTelemetry.isLoading}
            error={latestTelemetry.isError}
          />
        </Grid>
      </Grid>

      <RecentAlerts />
    </Box>
  );
}
