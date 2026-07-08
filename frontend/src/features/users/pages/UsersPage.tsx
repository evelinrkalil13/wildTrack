import { useState } from "react";
import {
  Alert,
  Box,
  Chip,
  InputAdornment,
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
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import { useAuth } from "@/store/auth.context";
import { UserRole } from "@/api/types/enums";
import { useUsers } from "../hooks/useUsers";
import { useUpdateUserRole } from "../hooks/useUpdateUserRole";
import type { ApiError } from "@/api/types/common.types";

const ROLE_LABELS: Record<UserRole, string> = {
  [UserRole.admin]: "Admin",
  [UserRole.researcher]: "Investigador",
  [UserRole.field_operator]: "Operador",
};

const ROLE_COLOR: Record<UserRole, "error" | "warning" | "default"> = {
  [UserRole.admin]: "error",
  [UserRole.researcher]: "warning",
  [UserRole.field_operator]: "default",
};

interface SnackState { open: boolean; message: string; severity: "success" | "error" }

export default function UsersPage() {
  const { user: me } = useAuth();

  const [page, setPage]         = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch]     = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [snack, setSnack]       = useState<SnackState>({ open: false, message: "", severity: "success" });

  const { data, isLoading, isError } = useUsers({ page, pageSize, search });
  const updateRole = useUpdateUserRole();

  function applySearch() {
    setPage(1);
    setSearch(searchInput.trim());
  }

  function handleRoleChange(userId: string, role: UserRole) {
    updateRole.mutate(
      { userId, data: { role } },
      {
        onSuccess: () => setSnack({ open: true, message: "Rol actualizado", severity: "success" }),
        onError: (err) => {
          const e = err as unknown as ApiError;
          const msg = e?.code === "CANNOT_CHANGE_OWN_ROLE"
            ? "No puedes cambiar tu propio rol"
            : e?.message ?? "Error al actualizar rol";
          setSnack({ open: true, message: msg, severity: "error" });
        },
      }
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight={700} mb={3}>
        Usuarios
      </Typography>

      <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
        <TextField
          placeholder="Buscar por nombre o email…"
          size="small"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && applySearch()}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
          sx={{ width: 320 }}
        />
      </Box>

      <Paper sx={{ bgcolor: "background.paper" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Nombre</TableCell>
              <TableCell>Email</TableCell>
              <TableCell sx={{ width: 180 }}>Rol</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading &&
              Array.from({ length: pageSize }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell><Skeleton /></TableCell>
                  <TableCell><Skeleton /></TableCell>
                  <TableCell><Skeleton /></TableCell>
                </TableRow>
              ))}

            {isError && (
              <TableRow>
                <TableCell colSpan={3}>
                  <Alert severity="error">Error al cargar usuarios</Alert>
                </TableCell>
              </TableRow>
            )}

            {!isLoading && !isError && data?.items.map((u) => {
              const isMe = u.id === me?.id;
              return (
                <TableRow key={u.id} hover>
                  <TableCell>{u.name}</TableCell>
                  <TableCell>{u.email}</TableCell>
                  <TableCell>
                    {isMe ? (
                      <Chip
                        label={ROLE_LABELS[u.role]}
                        color={ROLE_COLOR[u.role]}
                        size="small"
                      />
                    ) : (
                      <Select
                        value={u.role}
                        size="small"
                        variant="standard"
                        disableUnderline
                        onChange={(e) => handleRoleChange(u.id, e.target.value as UserRole)}
                        disabled={updateRole.isPending}
                        sx={{ fontSize: "0.875rem" }}
                      >
                        {Object.values(UserRole).map((r) => (
                          <MenuItem key={r} value={r}>
                            {ROLE_LABELS[r]}
                          </MenuItem>
                        ))}
                      </Select>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>

        {data && (
          <TablePagination
            component="div"
            count={data.total}
            page={page - 1}
            rowsPerPage={pageSize}
            rowsPerPageOptions={[10, 25, 50]}
            onPageChange={(_, p) => setPage(p + 1)}
            onRowsPerPageChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
            labelRowsPerPage="Filas"
          />
        )}
      </Paper>

      <Snackbar
        open={snack.open}
        autoHideDuration={4000}
        onClose={() => setSnack((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert severity={snack.severity} variant="filled" onClose={() => setSnack((s) => ({ ...s, open: false }))}>
          {snack.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
