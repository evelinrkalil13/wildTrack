import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Skeleton,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import { useAlerts } from "../hooks/useAlerts";
import { useResolveAlert } from "../hooks/useAlertMutations";
import { AlertType, type AlertFilter } from "../api/alerts.types";
import type { ApiError } from "@/api/types/common.types";

interface SnackbarState { open: boolean; message: string; severity: "success" | "error" }

const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  [AlertType.rfid_read_failure]:  "Falla RFID",
  [AlertType.connectivity_lost]:  "Sin conexión",
  [AlertType.sensor_failure]:     "Falla sensor",
  [AlertType.inactive_station]:   "Estación inactiva",
  [AlertType.empty_tank]:         "Depósito vacío",
  [AlertType.camera_failure]:     "Falla cámara",
};

const ALERT_TYPE_COLORS: Record<AlertType, "error" | "warning" | "default"> = {
  [AlertType.connectivity_lost]:  "error",
  [AlertType.empty_tank]:         "error",
  [AlertType.rfid_read_failure]:  "warning",
  [AlertType.sensor_failure]:     "warning",
  [AlertType.camera_failure]:     "warning",
  [AlertType.inactive_station]:   "default",
};

function AlertTypeChip({ type }: { type: AlertType }) {
  return (
    <Chip
      label={ALERT_TYPE_LABELS[type] ?? type}
      color={ALERT_TYPE_COLORS[type] ?? "default"}
      size="small"
    />
  );
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function AlertsPage() {
  const [page, setPage]         = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [filter, setFilter]     = useState<AlertFilter>("open");

  const [snackbar, setSnackbar] = useState<SnackbarState>({
    open: false, message: "", severity: "success",
  });

  const { data, isLoading, isError } = useAlerts({ page, pageSize, filter });
  const resolveMutation = useResolveAlert();

  function showSnackbar(message: string, severity: "success" | "error") {
    setSnackbar({ open: true, message, severity });
  }

  function handleResolve(id: string) {
    resolveMutation.mutate(id, {
      onSuccess: () => showSnackbar("Alerta marcada como resuelta", "success"),
      onError: (err) => {
        const e = err as unknown as ApiError;
        if (e.status === 403) {
          showSnackbar("No tienes permiso para resolver alertas", "error");
        } else {
          showSnackbar(e.message ?? "Error al resolver la alerta", "error");
        }
      },
    });
  }

  const rows = data?.items ?? [];
  const totalRows = data?.total ?? 0;

  return (
    <Box sx={{ p: 3 }}>
      {/* Toolbar */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>
          Alertas
        </Typography>

        <ToggleButtonGroup
          value={filter}
          exclusive
          size="small"
          onChange={(_, v) => {
            if (v) { setFilter(v); setPage(1); }
          }}
        >
          <ToggleButton value="open">Abiertas</ToggleButton>
          <ToggleButton value="resolved">Resueltas</ToggleButton>
          <ToggleButton value="all">Todas</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Table */}
      <Paper
        elevation={0}
        sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3, overflow: "hidden" }}
      >
        {isError && (
          <Alert severity="error" sx={{ m: 2 }}>
            Error al cargar las alertas. Intenta recargar la página.
          </Alert>
        )}

        <Box sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Tipo</TableCell>
                <TableCell>Mensaje</TableCell>
                <TableCell>Estación</TableCell>
                <TableCell>Dispositivo</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell>Creada</TableCell>
                <TableCell align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading &&
                Array.from({ length: Math.min(pageSize, 5) }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 7 }).map((_, j) => (
                      <TableCell key={j}><Skeleton variant="text" /></TableCell>
                    ))}
                  </TableRow>
                ))}

              {!isLoading && rows.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={7}
                    align="center"
                    sx={{ py: 5, color: "text.secondary" }}
                  >
                    {filter === "open"
                      ? "No hay alertas abiertas"
                      : filter === "resolved"
                      ? "No hay alertas resueltas"
                      : "No hay alertas registradas"}
                  </TableCell>
                </TableRow>
              )}

              {!isLoading &&
                rows.map((alert) => {
                  const isResolving =
                    resolveMutation.isPending &&
                    resolveMutation.variables === alert.alert_id;

                  return (
                    <TableRow key={alert.alert_id} hover>
                      <TableCell>
                        <AlertTypeChip type={alert.alert_type} />
                      </TableCell>

                      <TableCell sx={{ maxWidth: 260 }}>
                        <Typography
                          variant="body2"
                          sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                          title={alert.message}
                        >
                          {alert.message}
                        </Typography>
                      </TableCell>

                      <TableCell>
                        <Typography
                          variant="body2"
                          color={alert.station_id ? "text.primary" : "text.disabled"}
                          sx={{ fontFamily: alert.station_id ? "monospace" : undefined, fontSize: "0.75rem" }}
                        >
                          {alert.station_id ? alert.station_id.slice(0, 8) + "…" : "—"}
                        </Typography>
                      </TableCell>

                      <TableCell>
                        <Typography
                          variant="body2"
                          color={alert.device_id ? "text.primary" : "text.disabled"}
                          sx={{ fontFamily: alert.device_id ? "monospace" : undefined, fontSize: "0.75rem" }}
                        >
                          {alert.device_id ? alert.device_id.slice(0, 8) + "…" : "—"}
                        </Typography>
                      </TableCell>

                      <TableCell>
                        <Chip
                          label={alert.resolved ? "Resuelta" : "Abierta"}
                          color={alert.resolved ? "success" : "warning"}
                          size="small"
                        />
                      </TableCell>

                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {formatDate(alert.created_at)}
                        </Typography>
                      </TableCell>

                      <TableCell align="right">
                        {!alert.resolved && (
                          <Tooltip title="Marcar como resuelta">
                            <span>
                              <Button
                                size="small"
                                variant="outlined"
                                color="success"
                                disabled={isResolving}
                                startIcon={
                                  isResolving
                                    ? <CircularProgress size={14} color="inherit" />
                                    : <CheckCircleOutlineIcon fontSize="small" />
                                }
                                onClick={() => handleResolve(alert.alert_id)}
                              >
                                Resolver
                              </Button>
                            </span>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
            </TableBody>
          </Table>
        </Box>

        <TablePagination
          component="div"
          count={totalRows}
          page={page - 1}
          onPageChange={(_, newPage) => setPage(newPage + 1)}
          rowsPerPage={pageSize}
          onRowsPerPageChange={(e) => { setPageSize(+e.target.value); setPage(1); }}
          rowsPerPageOptions={[10, 25, 50]}
          labelRowsPerPage="Filas:"
          labelDisplayedRows={({ from, to, count }) => `${from}–${to} de ${count}`}
        />
      </Paper>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          severity={snackbar.severity}
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          sx={{ width: "100%" }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
