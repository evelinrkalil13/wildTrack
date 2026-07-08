import { useMemo, useState } from "react";
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
import PeopleIcon from "@mui/icons-material/People";
import { useStations } from "../hooks/useStations";
import { useDeleteStation } from "../hooks/useStationMutations";
import StationFormDialog from "../components/StationFormDialog";
import StationStatusChip from "../components/StationStatusChip";
import MembersDialog from "@/features/members/components/MembersDialog";
import ConfirmDialog from "@/components/ConfirmDialog";
import { useAllZones } from "@/features/zones/hooks/useZones";
import type { StationRead } from "../api/stations.types";
import { useAuth } from "@/store/auth.context";
import { StationStatus, UserRole } from "@/api/types/enums";
import type { ApiError } from "@/api/types/common.types";

interface SnackbarState { open: boolean; message: string; severity: "success" | "error" }

const STATUS_LABELS: Record<StationStatus, string> = {
  [StationStatus.active]:      "Activa",
  [StationStatus.inactive]:    "Inactiva",
  [StationStatus.maintenance]: "Mantenimiento",
  [StationStatus.offline]:     "Desconectada",
};

function formatCoords(lat: number, lng: number) {
  return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("es-CO", { dateStyle: "medium" });
}

export default function StationsPage() {
  const { user } = useAuth();
  const isAdmin      = user?.role === UserRole.admin;
  const isResearcher = user?.role === UserRole.researcher;
  const canCreate    = isAdmin || isResearcher;

  const [page, setPage]           = useState(1);
  const [pageSize, setPageSize]   = useState(10);
  const [statusFilter, setStatusFilter] = useState<StationStatus | "">("");

  const [formOpen, setFormOpen]           = useState(false);
  const [editTarget, setEditTarget]       = useState<StationRead | undefined>();
  const [deleteTarget, setDeleteTarget]   = useState<StationRead | null>(null);
  const [membersStation, setMembersStation] = useState<StationRead | null>(null);
  const [snackbar, setSnackbar]           = useState<SnackbarState>({ open: false, message: "", severity: "success" });

  const { data, isLoading, isError } = useStations({
    page,
    pageSize,
    status: statusFilter || undefined,
  });
  const { data: allZones } = useAllZones();
  const deleteMutation = useDeleteStation();

  const zoneMap = useMemo(
    () => Object.fromEntries((allZones ?? []).map((z) => [z.id, z.name])),
    [allZones]
  );

  function showSnackbar(message: string, severity: "success" | "error") {
    setSnackbar({ open: true, message, severity });
  }

  function handleEdit(station: StationRead) {
    setEditTarget(station);
    setFormOpen(true);
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
        showSnackbar("Estación eliminada correctamente", "success");
      },
      onError: (err) => {
        setDeleteTarget(null);
        const e = err as unknown as ApiError;
        showSnackbar(e.message ?? "Error al eliminar la estación", "error");
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
          Estaciones
        </Typography>

        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Estado</InputLabel>
          <Select
            value={statusFilter}
            label="Estado"
            onChange={(e) => { setStatusFilter(e.target.value as StationStatus | ""); setPage(1); }}
          >
            <MenuItem value="">Todos</MenuItem>
            {Object.values(StationStatus).map((s) => (
              <MenuItem key={s} value={s}>{STATUS_LABELS[s]}</MenuItem>
            ))}
          </Select>
        </FormControl>

        {canCreate && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => { setEditTarget(undefined); setFormOpen(true); }}
          >
            Nueva estación
          </Button>
        )}
      </Box>

      {/* Table */}
      <Paper elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3, overflow: "hidden" }}>
        {isError && (
          <Alert severity="error" sx={{ m: 2 }}>
            Error al cargar las estaciones. Intenta recargar la página.
          </Alert>
        )}

        <Box sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Código</TableCell>
                <TableCell>Nombre</TableCell>
                <TableCell>Zona</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell>Coordenadas</TableCell>
                <TableCell>Creada</TableCell>
                <TableCell align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading &&
                Array.from({ length: pageSize > 5 ? 5 : pageSize }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 7 }).map((_, j) => (
                      <TableCell key={j}><Skeleton variant="text" /></TableCell>
                    ))}
                  </TableRow>
                ))}

              {!isLoading && rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 5, color: "text.secondary" }}>
                    {statusFilter
                      ? `Sin estaciones con estado "${STATUS_LABELS[statusFilter]}"`
                      : "No hay estaciones registradas"}
                  </TableCell>
                </TableRow>
              )}

              {!isLoading && rows.map((station) => (
                <TableRow key={station.id} hover>
                  <TableCell>
                    <Typography
                      variant="body2"
                      sx={{ fontFamily: "monospace", fontWeight: 600, letterSpacing: 0.5 }}
                    >
                      {station.code}
                    </Typography>
                  </TableCell>
                  <TableCell>{station.name}</TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {zoneMap[station.zone_id] ?? "—"}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <StationStatusChip status={station.status} />
                  </TableCell>
                  <TableCell sx={{ fontFamily: "monospace", fontSize: "0.78rem" }}>
                    {formatCoords(station.latitude, station.longitude)}
                  </TableCell>
                  <TableCell>{formatDate(station.created_at)}</TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 0.5 }}>
                      <Tooltip title="Miembros">
                        <IconButton size="small" onClick={() => setMembersStation(station)}>
                          <PeopleIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Editar">
                        <IconButton size="small" onClick={() => handleEdit(station)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {isAdmin && (
                        <Tooltip title="Eliminar">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => setDeleteTarget(station)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
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
      <MembersDialog
        open={!!membersStation}
        station={membersStation}
        onClose={() => setMembersStation(null)}
      />

      <StationFormDialog
        open={formOpen}
        initialData={editTarget}
        onClose={handleCloseForm}
        onSaved={() => showSnackbar(
          editTarget ? "Estación actualizada correctamente" : "Estación creada correctamente",
          "success"
        )}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        title="Eliminar estación"
        description={
          deleteTarget
            ? `¿Eliminar la estación "${deleteTarget.name}" (${deleteTarget.code})? Esta acción no se puede deshacer.`
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
