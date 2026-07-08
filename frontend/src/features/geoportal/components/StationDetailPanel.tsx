import {
  Box,
  Chip,
  Divider,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import RouterIcon from "@mui/icons-material/Router";
import ThermostatIcon from "@mui/icons-material/Thermostat";
import RssFeedIcon from "@mui/icons-material/RssFeed";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import type { GeoportalStationRead } from "../api/geoportal.types";
import { DeviceStatus, StationStatus } from "@/api/types/enums";

const STATUS_LABELS: Record<StationStatus, string> = {
  [StationStatus.active]:      "Activa",
  [StationStatus.inactive]:    "Inactiva",
  [StationStatus.maintenance]: "Mantenimiento",
  [StationStatus.offline]:     "Desconectada",
};

const STATUS_COLORS: Record<StationStatus, "success" | "warning" | "default" | "error"> = {
  [StationStatus.active]:      "success",
  [StationStatus.maintenance]: "warning",
  [StationStatus.offline]:     "default",
  [StationStatus.inactive]:    "default",
};

const DEVICE_STATUS_LABELS: Record<DeviceStatus, string> = {
  [DeviceStatus.online]:     "En línea",
  [DeviceStatus.offline]:    "Desconectado",
  [DeviceStatus.unassigned]: "Sin asignar",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
}

function formatCoords(lat: number, lng: number): string {
  return `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
}

interface StationDetailPanelProps {
  station: GeoportalStationRead;
  onClose: () => void;
}

export default function StationDetailPanel({ station, onClose }: StationDetailPanelProps) {
  return (
    <Box
      sx={{
        width: 340,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.paper",
        borderLeft: "1px solid",
        borderColor: "divider",
        overflow: "auto",
        zIndex: 1,
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: 2,
          py: 1.5,
          display: "flex",
          alignItems: "flex-start",
          gap: 1,
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            variant="caption"
            sx={{ fontFamily: "monospace", color: "primary.main", fontWeight: 600 }}
          >
            {station.station_code}
          </Typography>
          <Typography variant="subtitle1" fontWeight={700} noWrap>
            {station.station_name}
          </Typography>
        </Box>
        <IconButton size="small" onClick={onClose} sx={{ mt: 0.25 }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      <Box sx={{ flex: 1, overflow: "auto" }}>
        {/* Station Info */}
        <SectionBlock>
          <Stack spacing={0.75}>
            <Row label="Estado">
              <Chip
                label={STATUS_LABELS[station.status]}
                color={STATUS_COLORS[station.status]}
                size="small"
              />
            </Row>
            <Row label="Zona">{station.zone_name}</Row>
            <Row label="Coordenadas">
              <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: "0.78rem" }}>
                {formatCoords(station.latitude, station.longitude)}
              </Typography>
            </Row>
            {station.open_alerts_count > 0 && (
              <Box
                sx={{
                  mt: 0.5,
                  px: 1.5,
                  py: 0.75,
                  bgcolor: "warning.main",
                  borderRadius: 1.5,
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                }}
              >
                <NotificationsActiveIcon fontSize="small" sx={{ color: "warning.contrastText" }} />
                <Typography variant="body2" fontWeight={600} sx={{ color: "warning.contrastText" }}>
                  {station.open_alerts_count}{" "}
                  {station.open_alerts_count === 1 ? "alerta abierta" : "alertas abiertas"}
                </Typography>
              </Box>
            )}
          </Stack>
        </SectionBlock>

        <Divider />

        {/* Device */}
        <SectionBlock
          icon={<RouterIcon fontSize="small" sx={{ color: "text.secondary" }} />}
          title="Dispositivo"
        >
          {station.device ? (
            <Stack spacing={0.75}>
              <Row label="Serial">
                <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: "0.82rem" }}>
                  {station.device.serial_number}
                </Typography>
              </Row>
              <Row label="Estado">
                <Chip
                  label={DEVICE_STATUS_LABELS[station.device.status]}
                  color={station.device.status === DeviceStatus.online ? "success" : "default"}
                  size="small"
                />
              </Row>
              <Row label="Última conexión">{formatDate(station.device.last_seen)}</Row>
            </Stack>
          ) : (
            <EmptyHint text="Sin dispositivo asignado" />
          )}
        </SectionBlock>

        <Divider />

        {/* Telemetry */}
        <SectionBlock
          icon={<ThermostatIcon fontSize="small" sx={{ color: "text.secondary" }} />}
          title="Última telemetría"
        >
          {station.latest_telemetry ? (
            <Stack spacing={0.75}>
              {station.latest_telemetry.temperature_c !== null && (
                <Row label="Temperatura">{station.latest_telemetry.temperature_c?.toFixed(1)} °C</Row>
              )}
              {station.latest_telemetry.humidity_pct !== null && (
                <Row label="Humedad">{station.latest_telemetry.humidity_pct?.toFixed(1)} %</Row>
              )}
              {station.latest_telemetry.wifi_rssi_dbm !== null && (
                <Row label="RSSI Wi-Fi">{station.latest_telemetry.wifi_rssi_dbm} dBm</Row>
              )}
              {station.latest_telemetry.firmware_version && (
                <Row label="Firmware">
                  <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: "0.78rem" }}>
                    {station.latest_telemetry.firmware_version}
                  </Typography>
                </Row>
              )}
              <Row label="Registrado">{formatDate(station.latest_telemetry.timestamp)}</Row>
            </Stack>
          ) : (
            <EmptyHint text="Sin datos de telemetría" />
          )}
        </SectionBlock>

        <Divider />

        {/* Recent Events */}
        <SectionBlock
          icon={<RssFeedIcon fontSize="small" sx={{ color: "text.secondary" }} />}
          title="Eventos recientes"
        >
          {station.recent_events.length > 0 ? (
            <Stack spacing={1}>
              {station.recent_events.map((evt, idx) => (
                <Box
                  key={evt.event_id || idx}
                  sx={{
                    p: 1,
                    bgcolor: "background.default",
                    borderRadius: 1.5,
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                    {formatDate(evt.timestamp)}
                  </Typography>
                  {evt.rfid_tag && (
                    <Row label="RFID">
                      <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: "0.78rem" }}>
                        {evt.rfid_tag}
                      </Typography>
                    </Row>
                  )}
                  {evt.consumed_g !== null && evt.consumed_g !== undefined && (
                    <Row label="Consumo">{evt.consumed_g.toFixed(1)} g</Row>
                  )}
                  {evt.temperature_c !== null && evt.temperature_c !== undefined && (
                    <Row label="Temperatura">{evt.temperature_c.toFixed(1)} °C</Row>
                  )}
                  {evt.humidity_pct !== null && evt.humidity_pct !== undefined && (
                    <Row label="Humedad">{evt.humidity_pct.toFixed(1)} %</Row>
                  )}
                  {evt.media_urls.length > 0 && (
                    <Box sx={{ mt: 0.75 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                        Fotos ({evt.media_urls.length})
                      </Typography>
                      <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap" }}>
                        {evt.media_urls.slice(0, 4).map((url, i) => (
                          <Box
                            key={i}
                            component="img"
                            src={url}
                            alt={`Foto ${i + 1}`}
                            onClick={() => window.open(url, "_blank")}
                            onError={(e) => {
                              (e.currentTarget as HTMLImageElement).style.display = "none";
                            }}
                            sx={{
                              width: 72,
                              height: 72,
                              objectFit: "cover",
                              borderRadius: 1,
                              cursor: "pointer",
                              border: "1px solid",
                              borderColor: "divider",
                              "&:hover": { opacity: 0.85, borderColor: "primary.main" },
                            }}
                          />
                        ))}
                        {evt.media_urls.length > 4 && (
                          <Box
                            sx={{
                              width: 72,
                              height: 72,
                              borderRadius: 1,
                              border: "1px solid",
                              borderColor: "divider",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              bgcolor: "background.paper",
                              cursor: "pointer",
                            }}
                            onClick={() => window.open(evt.media_urls[4], "_blank")}
                          >
                            <Typography variant="caption" color="text.secondary">
                              +{evt.media_urls.length - 4}
                            </Typography>
                          </Box>
                        )}
                      </Box>
                    </Box>
                  )}
                </Box>
              ))}
            </Stack>
          ) : (
            <EmptyHint text="Sin eventos registrados" />
          )}
        </SectionBlock>
      </Box>
    </Box>
  );
}

function SectionBlock({
  icon,
  title,
  children,
}: {
  icon?: React.ReactNode;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <Box sx={{ px: 2, py: 1.5 }}>
      {title && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 1 }}>
          {icon}
          <Typography variant="caption" sx={{ textTransform: "uppercase", letterSpacing: 0.6, fontWeight: 600, color: "text.secondary" }}>
            {title}
          </Typography>
        </Box>
      )}
      {children}
    </Box>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, justifyContent: "space-between" }}>
      <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
        {label}
      </Typography>
      <Box sx={{ textAlign: "right" }}>
        {typeof children === "string" || typeof children === "number" ? (
          <Typography variant="body2">{children}</Typography>
        ) : (
          children
        )}
      </Box>
    </Box>
  );
}

function EmptyHint({ text }: { text: string }) {
  return (
    <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>
      {text}
    </Typography>
  );
}
