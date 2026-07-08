import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  IconButton,
  InputAdornment,
  Paper,
  Skeleton,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import SearchIcon from "@mui/icons-material/Search";
import { useZones } from "../hooks/useZones";
import { useDeleteZone } from "../hooks/useZoneMutations";
import ZoneFormDialog from "../components/ZoneFormDialog";
import ConfirmDialog from "@/components/ConfirmDialog";
import type { ZoneRead } from "../api/zones.types";
import { useAuth } from "@/store/auth.context";
import { UserRole } from "@/api/types/enums";
import type { ApiError } from "@/api/types/common.types";

interface SnackbarState { open: boolean; message: string; severity: "success" | "error" }

function formatCoords(lat: number, lng: number) {
  return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("es-CO", { dateStyle: "medium" });
}

export default function ZonesPage() {
  const { user } = useAuth();
  const isAdmin       = user?.role === UserRole.admin;
  const isResearcher  = user?.role === UserRole.researcher;
  const canWrite      = isAdmin || isResearcher;

  const [page, setPage]           = useState(1);
  const [pageSize, setPageSize]   = useState(10);
  const [country, setCountry]     = useState("");
  const [countryInput, setCountryInput] = useState("");

  const [formOpen, setFormOpen]   = useState(false);
  const [editTarget, setEditTarget]   = useState<ZoneRead | undefined>();
  const [deleteTarget, setDeleteTarget] = useState<ZoneRead | null>(null);
  const [snackbar, setSnackbar]   = useState<SnackbarState>({ open: false, message: "", severity: "success" });

  const { data, isLoading, isError } = useZones({ page, pageSize, country: country || undefined });
  const deleteMutation = useDeleteZone();

  function showSnackbar(message: string, severity: "success" | "error") {
    setSnackbar({ open: true, message, severity });
  }

  function handleEdit(zone: ZoneRead) {
    setEditTarget(zone);
    setFormOpen(true);
  }

  function handleCloseForm() {
    setFormOpen(false);
    setEditTarget(undefined);
  }

  function handleCountrySearch() {
    setCountry(countryInput.trim());
    setPage(1);
  }

  function handleDeleteConfirm() {
    if (!deleteTarget) return;
    deleteMutation.mutate(deleteTarget.id, {
      onSuccess: () => {
        setDeleteTarget(null);
        showSnackbar("Zona eliminada correctamente", "success");
      },
      onError: (err) => {
        setDeleteTarget(null);
        const e = err as unknown as ApiError;
        showSnackbar(e.message ?? "Error al eliminar la zona", "error");
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
          Zonas
        </Typography>

        <TextField
          size="small"
          placeholder="Filtrar por país"
          value={countryInput}
          onChange={(e) => setCountryInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCountrySearch()}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton size="small" onClick={handleCountrySearch}>
                  <SearchIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ),
          }}
          sx={{ width: 220 }}
        />

        {canWrite && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => { setEditTarget(undefined); setFormOpen(true); }}
          >
            Nueva zona
          </Button>
        )}
      </Box>

      {/* Table */}
      <Paper elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3, overflow: "hidden" }}>
        {isError && (
          <Alert severity="error" sx={{ m: 2 }}>
            Error al cargar las zonas. Intenta recargar la página.
          </Alert>
        )}

        <Box sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Nombre</TableCell>
                <TableCell>Ciudad</TableCell>
                <TableCell>País</TableCell>
                <TableCell>Municipio</TableCell>
                <TableCell>Altitud</TableCell>
                <TableCell>Coordenadas</TableCell>
                <TableCell>Creada</TableCell>
                <TableCell align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading &&
                Array.from({ length: pageSize > 5 ? 5 : pageSize }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 8 }).map((_, j) => (
                      <TableCell key={j}><Skeleton variant="text" /></TableCell>
                    ))}
                  </TableRow>
                ))}

              {!isLoading && rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 5, color: "text.secondary" }}>
                    {country ? `Sin resultados para "${country}"` : "No hay zonas registradas"}
                  </TableCell>
                </TableRow>
              )}

              {!isLoading && rows.map((zone) => (
                <TableRow key={zone.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {zone.name}
                    </Typography>
                  </TableCell>
                  <TableCell>{zone.city}</TableCell>
                  <TableCell>{zone.country}</TableCell>
                  <TableCell>{zone.municipality ?? "—"}</TableCell>
                  <TableCell>
                    {zone.altitude !== null ? `${zone.altitude} m` : "—"}
                  </TableCell>
                  <TableCell sx={{ fontFamily: "monospace", fontSize: "0.78rem" }}>
                    {formatCoords(zone.latitude, zone.longitude)}
                  </TableCell>
                  <TableCell>{formatDate(zone.created_at)}</TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 0.5 }}>
                      {canWrite && (
                        <Tooltip title="Editar">
                          <IconButton size="small" onClick={() => handleEdit(zone)}>
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {isAdmin && (
                        <Tooltip title="Eliminar">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => setDeleteTarget(zone)}
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
      <ZoneFormDialog
        open={formOpen}
        initialData={editTarget}
        onClose={handleCloseForm}
        onSaved={() => showSnackbar(
          editTarget ? "Zona actualizada correctamente" : "Zona creada correctamente",
          "success"
        )}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        title="Eliminar zona"
        description={
          deleteTarget
            ? `¿Eliminar la zona "${deleteTarget.name}"? Esta acción no se puede deshacer.`
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
