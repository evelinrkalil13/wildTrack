import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  IconButton,
  Paper,
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
import StorefrontIcon from "@mui/icons-material/Storefront";
import { useFoods } from "../hooks/useFoods";
import { useDeleteFood } from "../hooks/useFoodMutations";
import FoodFormDialog from "../components/FoodFormDialog";
import FoodStationsDialog from "../components/FoodStationsDialog";
import ConfirmDialog from "@/components/ConfirmDialog";
import type { FoodRead } from "../api/foods.types";
import { UserRole } from "@/api/types/enums";
import { useAuth } from "@/store/auth.context";
import type { ApiError } from "@/api/types/common.types";

interface SnackbarState { open: boolean; message: string; severity: "success" | "error" }

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("es-CO", { dateStyle: "medium" });
}

export default function FoodsPage() {
  const { user } = useAuth();
  const isAdmin      = user?.role === UserRole.admin;
  const canEdit      = isAdmin || user?.role === UserRole.researcher;

  const [page, setPage]         = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const [formOpen, setFormOpen]         = useState(false);
  const [editTarget, setEditTarget]     = useState<FoodRead | undefined>();
  const [deleteTarget, setDeleteTarget] = useState<FoodRead | null>(null);
  const [stationsFood, setStationsFood] = useState<FoodRead | null>(null);
  const [snackbar, setSnackbar]         = useState<SnackbarState>({
    open: false, message: "", severity: "success",
  });

  const { data, isLoading, isError } = useFoods({ page, pageSize });
  const deleteMutation = useDeleteFood();

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
        showSnackbar("Alimento eliminado correctamente", "success");
      },
      onError: (err) => {
        setDeleteTarget(null);
        const e = err as unknown as ApiError;
        if (e.code === "FOOD_IN_USE") {
          showSnackbar("No se puede eliminar: el alimento está asignado a una o más estaciones", "error");
        } else if (e.status === 403) {
          showSnackbar("No tienes permiso para eliminar alimentos", "error");
        } else {
          showSnackbar(e.message ?? "Error al eliminar el alimento", "error");
        }
      },
    });
  }

  const rows = data?.items ?? [];
  const totalRows = data?.total ?? 0;
  const colCount = canEdit ? 6 : 5;

  return (
    <Box sx={{ p: 3 }}>
      {/* Toolbar */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>
          Alimentos
        </Typography>

        {canEdit && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => { setEditTarget(undefined); setFormOpen(true); }}
          >
            Nuevo alimento
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
            Error al cargar los alimentos. Intenta recargar la página.
          </Alert>
        )}

        <Box sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Nombre</TableCell>
                <TableCell>Tipo</TableCell>
                <TableCell>Descripción</TableCell>
                <TableCell>Estaciones</TableCell>
                <TableCell>Registrado</TableCell>
                {canEdit && <TableCell align="right">Acciones</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading &&
                Array.from({ length: Math.min(pageSize, 5) }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: colCount }).map((_, j) => (
                      <TableCell key={j}><Skeleton variant="text" /></TableCell>
                    ))}
                  </TableRow>
                ))}

              {!isLoading && rows.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={colCount}
                    align="center"
                    sx={{ py: 5, color: "text.secondary" }}
                  >
                    No hay alimentos registrados
                  </TableCell>
                </TableRow>
              )}

              {!isLoading &&
                rows.map((food) => (
                  <TableRow key={food.id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {food.name}
                      </Typography>
                    </TableCell>

                    <TableCell>
                      <Typography variant="body2">{food.type}</Typography>
                    </TableCell>

                    <TableCell sx={{ maxWidth: 260 }}>
                      <Typography
                        variant="body2"
                        color={food.description ? "text.primary" : "text.disabled"}
                        sx={{
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {food.description ?? "—"}
                      </Typography>
                    </TableCell>

                    <TableCell>
                      <Tooltip title="Ver estaciones asociadas">
                        <Button
                          size="small"
                          variant="text"
                          color="inherit"
                          startIcon={<StorefrontIcon fontSize="small" />}
                          onClick={() => setStationsFood(food)}
                          sx={{ textTransform: "none", color: "text.secondary" }}
                        >
                          Ver
                        </Button>
                      </Tooltip>
                    </TableCell>

                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {formatDate(food.created_at)}
                      </Typography>
                    </TableCell>

                    {canEdit && (
                      <TableCell align="right">
                        <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 0.5 }}>
                          <Tooltip title="Editar">
                            <IconButton
                              size="small"
                              onClick={() => { setEditTarget(food); setFormOpen(true); }}
                            >
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          {isAdmin && (
                            <Tooltip title="Eliminar">
                              <IconButton
                                size="small"
                                color="error"
                                onClick={() => setDeleteTarget(food)}
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
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
      <FoodStationsDialog
        open={!!stationsFood}
        food={stationsFood}
        onClose={() => setStationsFood(null)}
      />

      <FoodFormDialog
        open={formOpen}
        initialData={editTarget}
        onClose={handleCloseForm}
        onSaved={() =>
          showSnackbar(
            editTarget ? "Alimento actualizado correctamente" : "Alimento creado correctamente",
            "success"
          )
        }
      />

      <ConfirmDialog
        open={!!deleteTarget}
        title="Eliminar alimento"
        description={
          deleteTarget
            ? `¿Eliminar "${deleteTarget.name}"? Si está asignado a una estación, la operación fallará.`
            : ""
        }
        loading={deleteMutation.isPending}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
      />

      <Snackbar
        open={snackbar.open}
        autoHideDuration={5000}
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
