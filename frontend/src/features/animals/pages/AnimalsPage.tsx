import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  FormControl,
  IconButton,
  InputAdornment,
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
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import SearchIcon from "@mui/icons-material/Search";
import { useAnimals } from "../hooks/useAnimals";
import { useDeleteAnimal } from "../hooks/useAnimalMutations";
import AnimalFormDialog from "../components/AnimalFormDialog";
import ConfirmDialog from "@/components/ConfirmDialog";
import type { AnimalRead } from "../api/animals.types";
import { AnimalSex, UserRole } from "@/api/types/enums";
import { useAuth } from "@/store/auth.context";
import type { ApiError } from "@/api/types/common.types";

interface SnackbarState { open: boolean; message: string; severity: "success" | "error" }

const SEX_LABELS: Record<AnimalSex, string> = {
  [AnimalSex.male]:    "Macho",
  [AnimalSex.female]:  "Hembra",
  [AnimalSex.unknown]: "Desconocido",
};

function SexChip({ sex }: { sex: AnimalSex }) {
  const colorMap: Record<AnimalSex, "info" | "secondary" | "default"> = {
    [AnimalSex.male]:    "info",
    [AnimalSex.female]:  "secondary",
    [AnimalSex.unknown]: "default",
  };
  return <Chip label={SEX_LABELS[sex]} color={colorMap[sex]} size="small" />;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("es-CO", { dateStyle: "medium" });
}

export default function AnimalsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === UserRole.admin;

  const [page, setPage]         = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [speciesInput, setSpeciesInput] = useState("");
  const [speciesFilter, setSpeciesFilter] = useState("");
  const [sexFilter, setSexFilter] = useState<AnimalSex | "">("");
  const [identifiedFilter, setIdentifiedFilter] = useState<"" | "true" | "false">("");

  const [formOpen, setFormOpen]       = useState(false);
  const [editTarget, setEditTarget]   = useState<AnimalRead | undefined>();
  const [deleteTarget, setDeleteTarget] = useState<AnimalRead | null>(null);
  const [snackbar, setSnackbar]       = useState<SnackbarState>({
    open: false, message: "", severity: "success",
  });

  const isIdentified =
    identifiedFilter === "" ? undefined : identifiedFilter === "true";

  const { data, isLoading, isError } = useAnimals({
    page,
    pageSize,
    species: speciesFilter || undefined,
    sex: sexFilter || undefined,
    isIdentified,
  });

  const deleteMutation = useDeleteAnimal();

  function showSnackbar(message: string, severity: "success" | "error") {
    setSnackbar({ open: true, message, severity });
  }

  function handleCloseForm() {
    setFormOpen(false);
    setEditTarget(undefined);
  }

  function handleSearch() {
    setSpeciesFilter(speciesInput.trim());
    setPage(1);
  }

  function handleDeleteConfirm() {
    if (!deleteTarget) return;
    deleteMutation.mutate(deleteTarget.id, {
      onSuccess: () => {
        setDeleteTarget(null);
        showSnackbar("Animal eliminado correctamente", "success");
      },
      onError: (err) => {
        setDeleteTarget(null);
        const e = err as unknown as ApiError;
        if (e.status === 403) {
          showSnackbar("No tienes permiso para eliminar animales", "error");
        } else {
          showSnackbar(e.message ?? "Error al eliminar el animal", "error");
        }
      },
    });
  }

  const rows = data?.items ?? [];
  const totalRows = data?.total ?? 0;
  const colCount = isAdmin ? 7 : 6;

  return (
    <Box sx={{ p: 3 }}>
      {/* Toolbar */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>
          Animales
        </Typography>

        <TextField
          size="small"
          placeholder="Buscar especie…"
          value={speciesInput}
          onChange={(e) => setSpeciesInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          sx={{ width: 200 }}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton size="small" onClick={handleSearch}>
                  <SearchIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />

        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>Sexo</InputLabel>
          <Select
            value={sexFilter}
            label="Sexo"
            onChange={(e) => { setSexFilter(e.target.value as AnimalSex | ""); setPage(1); }}
          >
            <MenuItem value="">Todos</MenuItem>
            {Object.values(AnimalSex).map((s) => (
              <MenuItem key={s} value={s}>{SEX_LABELS[s]}</MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Identificado</InputLabel>
          <Select
            value={identifiedFilter}
            label="Identificado"
            onChange={(e) => {
              setIdentifiedFilter(e.target.value as "" | "true" | "false");
              setPage(1);
            }}
          >
            <MenuItem value="">Todos</MenuItem>
            <MenuItem value="true">Identificados</MenuItem>
            <MenuItem value="false">Sin identificar</MenuItem>
          </Select>
        </FormControl>

        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => { setEditTarget(undefined); setFormOpen(true); }}
        >
          Registrar animal
        </Button>
      </Box>

      {/* RFID info note */}
      <Alert severity="info" sx={{ mb: 2 }}>
        La asociación con estaciones se genera automáticamente cuando el RFID del animal es
        detectado por un comedero.
      </Alert>

      {/* Table */}
      <Paper
        elevation={0}
        sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3, overflow: "hidden" }}
      >
        {isError && (
          <Alert severity="error" sx={{ m: 2 }}>
            Error al cargar los animales. Intenta recargar la página.
          </Alert>
        )}

        <Box sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Tag RFID</TableCell>
                <TableCell>Especie</TableCell>
                <TableCell>Sexo</TableCell>
                <TableCell>Edad estimada</TableCell>
                <TableCell>Identificado</TableCell>
                <TableCell>Registrado</TableCell>
                {isAdmin && <TableCell align="right">Acciones</TableCell>}
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
                    {speciesFilter || sexFilter || identifiedFilter !== ""
                      ? "Sin resultados para los filtros aplicados"
                      : "No hay animales registrados"}
                  </TableCell>
                </TableRow>
              )}

              {!isLoading &&
                rows.map((animal) => (
                  <TableRow key={animal.id} hover>
                    <TableCell>
                      {animal.rfid_tag ? (
                        <Typography
                          variant="body2"
                          sx={{ fontFamily: "monospace", fontWeight: 600 }}
                        >
                          {animal.rfid_tag}
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="text.disabled">—</Typography>
                      )}
                    </TableCell>

                    <TableCell>
                      <Typography variant="body2">{animal.species}</Typography>
                    </TableCell>

                    <TableCell>
                      <SexChip sex={animal.sex} />
                    </TableCell>

                    <TableCell>
                      <Typography
                        variant="body2"
                        color={animal.estimated_age ? "text.primary" : "text.disabled"}
                      >
                        {animal.estimated_age ?? "—"}
                      </Typography>
                    </TableCell>

                    <TableCell>
                      <Chip
                        label={animal.is_identified ? "Sí" : "No"}
                        color={animal.is_identified ? "success" : "default"}
                        size="small"
                      />
                    </TableCell>

                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {formatDate(animal.created_at)}
                      </Typography>
                    </TableCell>

                    {isAdmin && (
                      <TableCell align="right">
                        <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 0.5 }}>
                          <Tooltip title="Editar">
                            <IconButton
                              size="small"
                              onClick={() => { setEditTarget(animal); setFormOpen(true); }}
                            >
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Eliminar">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => setDeleteTarget(animal)}
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
      <AnimalFormDialog
        open={formOpen}
        initialData={editTarget}
        onClose={handleCloseForm}
        onSaved={() =>
          showSnackbar(
            editTarget ? "Animal actualizado correctamente" : "Animal registrado correctamente",
            "success"
          )
        }
      />

      <ConfirmDialog
        open={!!deleteTarget}
        title="Eliminar animal"
        description={
          deleteTarget
            ? `¿Eliminar el registro de "${deleteTarget.species}"${deleteTarget.rfid_tag ? ` (${deleteTarget.rfid_tag})` : ""}? Esta acción no se puede deshacer.`
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
