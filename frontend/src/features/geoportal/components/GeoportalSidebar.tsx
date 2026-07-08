import { useState } from "react";
import {
  Badge,
  Box,
  InputAdornment,
  List,
  ListItemButton,
  ListItemText,
  Skeleton,
  TextField,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import CellTowerIcon from "@mui/icons-material/CellTower";
import type { GeoportalStationRead } from "../api/geoportal.types";
import { StationStatus } from "@/api/types/enums";

const STATUS_DOT_COLOR: Record<StationStatus, string> = {
  [StationStatus.active]:      "#52b788",
  [StationStatus.maintenance]: "#e08a1e",
  [StationStatus.offline]:     "#5f7669",
  [StationStatus.inactive]:    "#5f7669",
};

interface GeoportalSidebarProps {
  stations: GeoportalStationRead[];
  selectedStationId: string | null;
  onSelect: (station: GeoportalStationRead) => void;
  isLoading: boolean;
}

export default function GeoportalSidebar({
  stations,
  selectedStationId,
  onSelect,
  isLoading,
}: GeoportalSidebarProps) {
  const [search, setSearch] = useState("");

  const filtered = stations.filter(
    (s) =>
      s.station_name.toLowerCase().includes(search.toLowerCase()) ||
      s.station_code.toLowerCase().includes(search.toLowerCase())
  );

  const total   = stations.length;
  const active  = stations.filter((s) => s.status === StationStatus.active).length;
  const alerted = stations.filter((s) => s.open_alerts_count > 0).length;

  return (
    <Box
      sx={{
        width: 280,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.paper",
        borderRight: "1px solid",
        borderColor: "divider",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box sx={{ px: 2, py: 1.5, borderBottom: "1px solid", borderColor: "divider" }}>
        <Typography variant="subtitle1" fontWeight={700} sx={{ fontFamily: "Space Grotesk" }}>
          Geoportal
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Estaciones de monitoreo
        </Typography>
      </Box>

      {/* KPI cards */}
      <Box sx={{ display: "flex", gap: 1, p: 1.5, borderBottom: "1px solid", borderColor: "divider" }}>
        <KpiCard label="Total" value={total} color="text.primary" loading={isLoading} />
        <KpiCard label="Activas" value={active} color="#52b788" loading={isLoading} />
        <KpiCard label="Alertas" value={alerted} color="#e08a1e" loading={isLoading} />
      </Box>

      {/* Search */}
      <Box sx={{ px: 1.5, py: 1 }}>
        <TextField
          size="small"
          fullWidth
          placeholder="Buscar estación..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" sx={{ color: "text.secondary" }} />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      {/* Station list */}
      <Box sx={{ flex: 1, overflow: "auto" }}>
        {isLoading ? (
          <Box sx={{ px: 1.5, py: 1 }}>
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} variant="text" height={48} sx={{ mb: 0.5 }} />
            ))}
          </Box>
        ) : filtered.length === 0 ? (
          <Box sx={{ p: 2, textAlign: "center" }}>
            <CellTowerIcon sx={{ color: "text.disabled", fontSize: 36, mb: 1 }} />
            <Typography variant="body2" color="text.secondary">
              {search ? "Sin resultados" : "Sin estaciones registradas"}
            </Typography>
          </Box>
        ) : (
          <List dense disablePadding>
            {filtered.map((station) => {
              const dotColor =
                station.open_alerts_count > 0
                  ? "#e08a1e"
                  : STATUS_DOT_COLOR[station.status];
              const isSelected = station.station_id === selectedStationId;

              return (
                <ListItemButton
                  key={station.station_id}
                  selected={isSelected}
                  onClick={() => onSelect(station)}
                  sx={{ px: 1.5, py: 0.75, gap: 1 }}
                >
                  {/* Status dot */}
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      bgcolor: dotColor,
                      flexShrink: 0,
                    }}
                  />
                  <ListItemText
                    primary={station.station_name}
                    secondary={station.station_code}
                    primaryTypographyProps={{ fontSize: "0.82rem", fontWeight: isSelected ? 600 : 400, noWrap: true }}
                    secondaryTypographyProps={{ fontSize: "0.73rem", fontFamily: "monospace" }}
                    sx={{ minWidth: 0 }}
                  />
                  {station.open_alerts_count > 0 && (
                    <Badge
                      badgeContent={station.open_alerts_count}
                      color="warning"
                      sx={{ "& .MuiBadge-badge": { fontSize: "0.65rem", height: 16, minWidth: 16 } }}
                    >
                      <Box sx={{ width: 16 }} />
                    </Badge>
                  )}
                </ListItemButton>
              );
            })}
          </List>
        )}
      </Box>
    </Box>
  );
}

function KpiCard({
  label,
  value,
  color,
  loading,
}: {
  label: string;
  value: number;
  color: string;
  loading: boolean;
}) {
  return (
    <Box
      sx={{
        flex: 1,
        bgcolor: "background.default",
        borderRadius: 2,
        p: 1,
        textAlign: "center",
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      {loading ? (
        <Skeleton variant="text" width="60%" sx={{ mx: "auto" }} />
      ) : (
        <Typography variant="h6" sx={{ color, fontWeight: 700, lineHeight: 1.2, fontSize: "1.1rem" }}>
          {value}
        </Typography>
      )}
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", fontSize: "0.68rem" }}>
        {label}
      </Typography>
    </Box>
  );
}
