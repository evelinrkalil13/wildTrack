import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import LinkIcon from "@mui/icons-material/Link";
import LinkOffIcon from "@mui/icons-material/LinkOff";
import { useDevices } from "../hooks/useDevices";
import { useDeleteDevice, useUnassignDevice } from "../hooks/useDeviceMutations";
import DeviceStatusChip from "../components/DeviceStatusChip";
import DeviceFormDialog from "../components/DeviceFormDialog";
import AssignStationDialog from "../components/AssignStationDialog";
import ConfirmDialog from "@/components/ConfirmDialog";
import type { DeviceRead } from "../api/devices.types";
import { useAuth } from "@/store/auth.context";
import { DeviceStatus, UserRole } from "@/api/types/enums";
import type { ApiError } from "@/api/types/common.types";

interface SnackbarState { open: boolean; message: string; severity: "success" | "error" }

const STATUS_LABELS: Record<DeviceStatus, string> = {
  [DeviceStatus.online]:     "Online",
  [DeviceStatus.offline]:    "Offline",
  [DeviceStatus.unassigned]: "Sin asignar",
};

function formatLastSeen(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "Ahora";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  return new Date(iso).toLocaleDateString("es-CO", { dateStyle: "medium" });
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("es-CO", { dateStyle: "medium" });
}

export default function DevicesPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === UserRole.admin;

  const [page, setPage]         = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<DeviceStatus | "">("");

  const [formOpen, setFormOpen]           = useState(false);
  const [editTarget, setEditTarget]       = useState<DeviceRead | undefined>();
  const [assignTarget, setAssignTarget]   = useState<DeviceRead | null>(null);
  const [unassignTarget, setUnassignTarget] = useState<DeviceRead | null>(null);
  const [deleteTarget, setDeleteTarget]   = useState<DeviceRead | null>(null);
  const [snackbar, setSnackbar]           = useState<SnackbarState>({ open: false, message: "", severity: "success" });

  const { data, isLoading, isError } = useDevices({
    page,
    pageSize,
    status: statusFilter || undefined,
  });

  const deleteMutation   = useDeleteDevice();
  const unassignMutation = useUnassignDevice();

  function showSnackbar(message: string, severity: "success" | "error") {
    setSnackbar({ open: true, message, severity });
  }

  function handleCloseForm() {
    setFormOpen(false);
    setEditTarget(undefined);
  }

  function handleDeleteConfirm() {
    if (!deleteTarget) return;
    deleteMutation.mutate(deleteTarget.id, {
      onSuccess: () => {
        setDeleteTarget(null);
        showSnackbar("Dispositivo eliminado correctamente", "success");
      },
      onError: (err) => {
        setDeleteTarget(null);
        const e = err as unknown as ApiError;
        showSnackbar(e.message ?? "Error al eliminar el dispositivo", "error");
      },
    });
  }

  function handleUnassignConfirm() {
    if (!unassignTarget) return;
    unassignMutation.mutate(unassignTarget.id, {
      onSuccess: () => {
        setUnassignTarget(null);
        showSnackbar("Dispositivo desasignado correctamente", "success");
      },
      onError: (err) => {
        setUnassignTarget(null);
        const e = err as unknown as ApiError;
        showSnackbar(e.message ?? "Error al desasignar el dispositivo", "error");
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
          Dispositivos
        </Typography>

        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Estado</InputLabel>
          <Select
            value={statusFilter}
            label="Estado"
            onChange={(e) => {
              setStatusFilter(e.target.value as DeviceStatus | "");
              setPage(1);
            }}
          >
            <MenuItem value="">Todos</MenuItem>
            {Object.values(DeviceStatus).map((s) => (
              <MenuItem key={s} value={s}>{STATUS_LABELS[s]}</MenuItem>
            ))}
          </Select>
        </FormControl>

        {isAdmin && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => { setEditTarget(undefined); setFormOpen(true); }}
          >
            Nuevo dispositivo
          </Button>
        )}
      </Box>

      {/* Table */}
      <Paper
        elevation={0}
        sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3, overflow: "hidden" }}
      >
        {isError && (
          <Alert severity="error" sx={{ m: 2 }}>
            Error al cargar los dispositivos. Intenta recargar la página.
          </Alert>
        )}

        <Box sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Serial</TableCell>
                <TableCell>Nombre</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell>Estación</TableCell>
                <TableCell>Última conexión</TableCell>
                <TableCell>Registrado</TableCell>
                {isAdmin && <TableCell align="right">Acciones</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading &&
                Array.from({ length: Math.min(pageSize, 5) }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: isAdmin ? 7 : 6 }).map((_, j) => (
                      <TableCell key={j}><Skeleton variant="text" /></TableCell>
                    ))}
                  </TableRow>
                ))}

              {!isLoading && rows.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={isAdmin ? 7 : 6}
                    align="center"
                    sx={{ py: 5, color: "text.secondary" }}
                  >
                    {statusFilter
                      ? `Sin dispositivos con estado "${STATUS_LABELS[statusFilter]}"`
                      : "No hay dispositivos registrados"}
                  </TableCell>
                </TableRow>
              )}

              {!isLoading &&
                rows.map((device) => (
                  <TableRow key={device.id} hover>
                    <TableCell>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "monospace", fontWeight: 600 }}
                      >
                        {device.serial_number}
                      </Typography>
                    </TableCell>

                    <TableCell>
                      <Typography variant="body2" color={device.name ? "text.primary" : "text.disabled"}>
                        {device.name ?? "—"}
                      </Typography>
                    </TableCell>

                    <TableCell>
                      <DeviceStatusChip status={device.status} />
                    </TableCell>

                    <TableCell>
                      {device.station_code ? (
                        <Typography
                          variant="body2"
                          sx={{ fontFamily: "monospace", fontWeight: 500 }}
                        >
                          {device.station_code}
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="text.disabled">—</Typography>
                      )}
                    </TableCell>

                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {formatLastSeen(device.last_seen)}
                      </Typography>
                    </TableCell>

                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {formatDate(device.created_at)}
                      </Typography>
                    </TableCell>

                    {isAdmin && (
                      <TableCell align="right">
                        <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 0.5 }}>
                          <Tooltip title="Editar nombre">
                            <IconButton
                              size="small"
                              onClick={() => { setEditTarget(device); setFormOpen(true); }}
                            >
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>

                          {device.station_id ? (
                            <Tooltip title="Desasignar estación">
                              <IconButton
                                size="small"
                                color="warning"
                                onClick={() => setUnassignTarget(device)}
                              >
                                <LinkOffIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          ) : (
                            <Tooltip title="Asignar a estación">
                              <IconButton
                                size="small"
                                color="primary"
                                onClick={() => setAssignTarget(device)}
                              >
                                <LinkIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}

                          <Tooltip title="Eliminar">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => setDeleteTarget(device)}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
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

      {/* Dialogs */}
      <DeviceFormDialog
        open={formOpen}
        initialData={editTarget}
        onClose={handleCloseForm}
        onSaved={() =>
          showSnackbar(
            editTarget
              ? "Dispositivo actualizado correctamente"
              : "Dispositivo creado correctamente",
            "success"
          )
        }
      />

      <AssignStationDialog
        open={!!assignTarget}
        device={assignTarget}
        onClose={() => setAssignTarget(null)}
        onSaved={() => showSnackbar("Dispositivo asignado correctamente", "success")}
      />

      <ConfirmDialog
        open={!!unassignTarget}
        title="Desasignar dispositivo"
        description={
          unassignTarget
            ? `¿Desasignar "${unassignTarget.serial_number}" de la estación ${unassignTarget.station_code ?? ""}?`
            : ""
        }
        confirmLabel="Desasignar"
        confirmColor="warning"
        loading={unassignMutation.isPending}
        onConfirm={handleUnassignConfirm}
        onCancel={() => setUnassignTarget(null)}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        title="Eliminar dispositivo"
        description={
          deleteTarget
            ? `¿Eliminar el dispositivo "${deleteTarget.serial_number}"? Esta acción no se puede deshacer.`
            : ""
        }
        loading={deleteMutation.isPending}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
      />

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
