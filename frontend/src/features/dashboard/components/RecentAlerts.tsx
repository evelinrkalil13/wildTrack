import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { AlertType } from "../api/dashboard.types";
import type { AlertRead } from "../api/dashboard.types";
import { useRecentAlerts } from "../hooks/useDashboardStats";

const TYPE_LABEL: Record<AlertType, string> = {
  [AlertType.rfid_read_failure]: "Falla RFID",
  [AlertType.connectivity_lost]: "Sin conexión",
  [AlertType.sensor_failure]: "Falla sensor",
  [AlertType.inactive_station]: "Estación inactiva",
  [AlertType.empty_tank]: "Depósito vacío",
  [AlertType.camera_failure]: "Falla cámara",
};

const TYPE_COLOR: Record<AlertType, "error" | "warning" | "default"> = {
  [AlertType.connectivity_lost]: "error",
  [AlertType.empty_tank]: "error",
  [AlertType.rfid_read_failure]: "warning",
  [AlertType.sensor_failure]: "warning",
  [AlertType.camera_failure]: "warning",
  [AlertType.inactive_station]: "default",
};

function AlertRow({ alert }: { alert: AlertRead }) {
  const color = TYPE_COLOR[alert.alert_type] ?? "default";
  const date = new Date(alert.created_at).toLocaleString("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
  });
  return (
    <TableRow hover>
      <TableCell>
        <Chip
          label={TYPE_LABEL[alert.alert_type] ?? alert.alert_type}
          color={color}
          size="small"
          variant="outlined"
        />
      </TableCell>
      <TableCell sx={{ maxWidth: 320 }}>
        <Typography variant="body2" noWrap title={alert.message}>
          {alert.message}
        </Typography>
      </TableCell>
      <TableCell>
        <Typography variant="body2" color="text.secondary">
          {alert.station_id ?? "—"}
        </Typography>
      </TableCell>
      <TableCell>
        <Typography variant="body2" color="text.secondary">
          {date}
        </Typography>
      </TableCell>
    </TableRow>
  );
}

export default function RecentAlerts() {
  const { data, isLoading, isError, refetch } = useRecentAlerts();

  return (
    <Paper
      elevation={0}
      sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3, overflow: "hidden" }}
    >
      <Box sx={{ px: 2.5, py: 2, borderBottom: "1px solid", borderColor: "divider" }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          Alertas recientes
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Últimas 5 sin resolver
        </Typography>
      </Box>

      {isError && (
        <Box sx={{ p: 2 }}>
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={() => refetch()}>
                Reintentar
              </Button>
            }
          >
            No se pudieron cargar las alertas.
          </Alert>
        </Box>
      )}

      {!isError && (
        <Box sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Tipo</TableCell>
                <TableCell>Mensaje</TableCell>
                <TableCell>Estación</TableCell>
                <TableCell>Fecha</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading &&
                [0, 1, 2].map((i) => (
                  <TableRow key={i}>
                    {[0, 1, 2, 3].map((j) => (
                      <TableCell key={j}>
                        <Skeleton variant="text" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}

              {!isLoading && (!data || data.length === 0) && (
                <TableRow>
                  <TableCell
                    colSpan={4}
                    align="center"
                    sx={{ py: 4, color: "text.secondary" }}
                  >
                    Sin alertas abiertas
                  </TableCell>
                </TableRow>
              )}

              {!isLoading &&
                data &&
                data.map((alert) => (
                  <AlertRow key={alert.alert_id} alert={alert} />
                ))}
            </TableBody>
          </Table>
        </Box>
      )}
    </Paper>
  );
}
