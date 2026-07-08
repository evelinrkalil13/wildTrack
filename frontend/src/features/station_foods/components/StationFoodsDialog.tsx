import { useState } from "react";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
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
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import GrassIcon from "@mui/icons-material/Grass";
import type { StationRead } from "@/features/stations/api/stations.types";
import { useStationFoods } from "../hooks/useStationFoods";
import {
  useActivateStationFood,
  useAddFoodToStation,
  useDeactivateStationFood,
  useRemoveStationFood,
} from "../hooks/useStationFoodMutations";
import { useAllFoods } from "@/features/foods/hooks/useAllFoods";
import type { FoodRead } from "@/features/foods/api/foods.types";
import type { ApiError } from "@/api/types/common.types";

interface SnackbarState { open: boolean; message: string; severity: "success" | "error" }

function errorMessage(err: unknown, fallback: string): string {
  const e = err as ApiError;
  if (e.status === 403)                  return "No tienes permiso para administrar los alimentos de esta estación";
  if (e.code === "FOOD_ALREADY_ASSOCIATED") return "Este alimento ya está asignado a esta estación";
  if (e.code === "CANNOT_REMOVE_ACTIVE")    return "Debes desactivar el alimento antes de eliminarlo";
  return e.message ?? fallback;
}

interface StationFoodsDialogProps {
  open: boolean;
  station: StationRead | null;
  onClose: () => void;
}

export default function StationFoodsDialog({ open, station, onClose }: StationFoodsDialogProps) {
  const stationId = station?.id ?? null;

  const [page, setPage]     = useState(1);
  const [pageSize]           = useState(10);
  const [selectedFood, setSelectedFood] = useState<FoodRead | null>(null);
  const [snackbar, setSnackbar] = useState<SnackbarState>({ open: false, message: "", severity: "success" });

  const { data, isLoading, isError } = useStationFoods(stationId, page, pageSize);
  const { data: allFoods, isLoading: foodsLoading } = useAllFoods();

  const addMutation        = useAddFoodToStation(stationId ?? "");
  const activateMutation   = useActivateStationFood(stationId ?? "");
  const deactivateMutation = useDeactivateStationFood(stationId ?? "");
  const removeMutation     = useRemoveStationFood(stationId ?? "");

  function showSnackbar(message: string, severity: "success" | "error") {
    setSnackbar({ open: true, message, severity });
  }

  function handleAdd() {
    if (!selectedFood || !stationId) return;
    addMutation.mutate(
      { food_id: selectedFood.id, active: true },
      {
        onSuccess: () => {
          setSelectedFood(null);
          showSnackbar("Alimento asignado correctamente", "success");
        },
        onError: (err) => showSnackbar(errorMessage(err, "Error al asignar alimento"), "error"),
      }
    );
  }

  function handleToggleActive(sfId: string, currentlyActive: boolean) {
    const mutation = currentlyActive ? deactivateMutation : activateMutation;
    mutation.mutate(sfId, {
      onSuccess: () =>
        showSnackbar(
          currentlyActive ? "Alimento desactivado" : "Alimento activado",
          "success"
        ),
      onError: (err) => showSnackbar(errorMessage(err, "Error al cambiar estado"), "error"),
    });
  }

  function handleRemove(sfId: string) {
    removeMutation.mutate(sfId, {
      onSuccess: () => showSnackbar("Alimento eliminado de la estación", "success"),
      onError: (err) => showSnackbar(errorMessage(err, "Error al eliminar alimento"), "error"),
    });
  }

  const rows = data?.items ?? [];
  const total = data?.total ?? 0;

  // Foods already assigned to this station — filter them out of the Autocomplete
  const assignedFoodIds = new Set(rows.map((r) => r.food_id));
  const availableFoods = (allFoods ?? []).filter((f) => !assignedFoodIds.has(f.id));

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth PaperProps={{ sx: { minHeight: 460 } }}>
        <DialogTitle sx={{ pr: 6 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <GrassIcon fontSize="small" color="primary" />
            Alimentos de "{station?.name}"
          </Box>
          <IconButton size="small" onClick={onClose} sx={{ position: "absolute", top: 12, right: 12 }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>

        <DialogContent sx={{ pb: 3 }}>
          {/* Add food form */}
          <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1.5, mb: 2, flexWrap: "wrap" }}>
            <Autocomplete
              options={availableFoods}
              loading={foodsLoading}
              value={selectedFood}
              onChange={(_, val) => setSelectedFood(val)}
              getOptionLabel={(f) => f.name}
              isOptionEqualToValue={(a, b) => a.id === b.id}
              renderOption={(props, f) => (
                <Box component="li" {...props} key={f.id}>
                  <Box>
                    <Typography variant="body2" fontWeight={600}>{f.name}</Typography>
                    <Typography variant="caption" color="text.secondary">{f.type}</Typography>
                  </Box>
                </Box>
              )}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Alimento"
                  size="small"
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {foodsLoading && <CircularProgress size={16} />}
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  }}
                />
              )}
              sx={{ flex: 1, minWidth: 220 }}
              noOptionsText={availableFoods.length === 0 ? "Todos los alimentos ya están asignados" : "Sin resultados"}
            />

            <Button
              variant="contained"
              startIcon={
                addMutation.isPending
                  ? <CircularProgress size={16} color="inherit" />
                  : <GrassIcon />
              }
              disabled={!selectedFood || addMutation.isPending}
              onClick={handleAdd}
              sx={{ height: 40, mt: 0.25 }}
            >
              Asignar
            </Button>
          </Box>

          <Divider sx={{ mb: 2 }} />

          {isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              Error al cargar los alimentos. Intenta recargar.
            </Alert>
          )}

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Nombre</TableCell>
                <TableCell>Tipo</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading &&
                Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i}>
                    {[1, 2, 3, 4].map((j) => (
                      <TableCell key={j}><Skeleton variant="text" /></TableCell>
                    ))}
                  </TableRow>
                ))}

              {!isLoading && rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} align="center" sx={{ py: 4, color: "text.secondary" }}>
                    No hay alimentos asignados a esta estación
                  </TableCell>
                </TableRow>
              )}

              {!isLoading && rows.map((sf) => {
                const isToggling =
                  (activateMutation.isPending && activateMutation.variables === sf.id) ||
                  (deactivateMutation.isPending && deactivateMutation.variables === sf.id);
                const isRemoving =
                  removeMutation.isPending && removeMutation.variables === sf.id;

                return (
                  <TableRow key={sf.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>{sf.food_name}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">{sf.food_type}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={sf.active ? "Activo" : "Inactivo"}
                        color={sf.active ? "success" : "default"}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 0.5 }}>
                        <Tooltip title={sf.active ? "Desactivar" : "Activar"}>
                          <span>
                            <Button
                              size="small"
                              variant="outlined"
                              color={sf.active ? "warning" : "success"}
                              disabled={isToggling}
                              onClick={() => handleToggleActive(sf.id, sf.active)}
                              sx={{ minWidth: 90, textTransform: "none", fontSize: "0.75rem" }}
                            >
                              {isToggling
                                ? <CircularProgress size={14} color="inherit" />
                                : sf.active ? "Desactivar" : "Activar"}
                            </Button>
                          </span>
                        </Tooltip>

                        <Tooltip title={sf.active ? "Desactiva antes de eliminar" : "Eliminar"}>
                          <span>
                            <IconButton
                              size="small"
                              color="error"
                              disabled={sf.active || isRemoving}
                              onClick={() => handleRemove(sf.id)}
                            >
                              {isRemoving
                                ? <CircularProgress size={16} color="inherit" />
                                : <DeleteIcon fontSize="small" />}
                            </IconButton>
                          </span>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          {total > pageSize && (
            <TablePagination
              component="div"
              count={total}
              page={page - 1}
              onPageChange={(_, p) => setPage(p + 1)}
              rowsPerPage={pageSize}
              rowsPerPageOptions={[pageSize]}
              labelDisplayedRows={({ from, to, count }) => `${from}–${to} de ${count}`}
            />
          )}
        </DialogContent>
      </Dialog>

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
    </>
  );
}
