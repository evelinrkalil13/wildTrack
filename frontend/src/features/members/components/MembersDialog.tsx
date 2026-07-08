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
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
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
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import { useMembers } from "../hooks/useMembers";
import {
  useAssignMember,
  useRemoveMember,
  useUpdateMemberRole,
} from "../hooks/useMemberMutations";
import { useAllUsers } from "@/features/users/hooks/useAllUsers";
import type { StationRead } from "@/features/stations/api/stations.types";
import type { MemberRead } from "../api/members.types";
import { StationUserRole } from "@/api/types/enums";
import type { ApiError } from "@/api/types/common.types";
import type { UserListItem } from "@/features/users/api/users.types";

interface SnackbarState { open: boolean; message: string; severity: "success" | "error" }

const ROLE_LABELS: Record<StationUserRole, string> = {
  [StationUserRole.owner]:          "Propietario",
  [StationUserRole.researcher]:     "Investigador",
  [StationUserRole.field_operator]: "Operador campo",
};

const ASSIGNABLE_ROLES = [
  StationUserRole.researcher,
  StationUserRole.field_operator,
] as const;

function errorMessage(err: unknown, fallback: string): string {
  const e = err as unknown as ApiError;
  if (e.status === 403)         return "No tienes permiso para administrar los miembros de esta estación";
  if (e.code === "ALREADY_MEMBER")       return "Este usuario ya es miembro de esta estación";
  if (e.code === "CANNOT_REMOVE_OWNER")  return "No se puede remover al propietario de la estación";
  if (e.code === "CANNOT_CHANGE_OWNER")  return "No se puede cambiar el rol del propietario";
  return e.message ?? fallback;
}

interface MembersDialogProps {
  open: boolean;
  station: StationRead | null;
  onClose: () => void;
}

export default function MembersDialog({ open, station, onClose }: MembersDialogProps) {
  const stationId = station?.id ?? null;

  const [page, setPage]         = useState(1);
  const [pageSize]               = useState(10);
  const [selectedUser, setSelectedUser] = useState<UserListItem | null>(null);
  const [addRole, setAddRole]   = useState<StationUserRole>(StationUserRole.researcher);
  const [snackbar, setSnackbar] = useState<SnackbarState>({ open: false, message: "", severity: "success" });

  const { data, isLoading, isError } = useMembers(stationId, page, pageSize);
  const { data: allUsers, isLoading: usersLoading } = useAllUsers();

  const assignMutation     = useAssignMember(stationId ?? "");
  const updateRoleMutation = useUpdateMemberRole(stationId ?? "");
  const removeMutation     = useRemoveMember(stationId ?? "");

  function showSnackbar(message: string, severity: "success" | "error") {
    setSnackbar({ open: true, message, severity });
  }

  function handleAdd() {
    if (!selectedUser || !stationId) return;
    assignMutation.mutate(
      { user_id: selectedUser.id, role: addRole },
      {
        onSuccess: () => {
          setSelectedUser(null);
          setAddRole(StationUserRole.researcher);
          showSnackbar("Miembro agregado correctamente", "success");
        },
        onError: (err) => showSnackbar(errorMessage(err, "Error al agregar miembro"), "error"),
      }
    );
  }

  function handleRoleChange(member: MemberRead, newRole: StationUserRole) {
    updateRoleMutation.mutate(
      { memberId: member.id, data: { role: newRole } },
      {
        onError: (err) => showSnackbar(errorMessage(err, "Error al cambiar rol"), "error"),
      }
    );
  }

  function handleRemove(member: MemberRead) {
    removeMutation.mutate(member.id, {
      onSuccess: () => showSnackbar("Miembro eliminado correctamente", "success"),
      onError: (err) => showSnackbar(errorMessage(err, "Error al eliminar miembro"), "error"),
    });
  }

  const members = data?.items ?? [];
  const totalMembers = data?.total ?? 0;

  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: { minHeight: 480 } }}
      >
        <DialogTitle sx={{ pr: 6 }}>
          Miembros de "{station?.name}"
          <IconButton
            size="small"
            onClick={onClose}
            sx={{ position: "absolute", top: 12, right: 12 }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>

        <DialogContent sx={{ pb: 3 }}>
          {/* Add member form */}
          <Box
            sx={{
              display: "flex",
              alignItems: "flex-start",
              gap: 1.5,
              mb: 2,
              flexWrap: "wrap",
            }}
          >
            <Autocomplete
              options={allUsers ?? []}
              loading={usersLoading}
              value={selectedUser}
              onChange={(_, val) => setSelectedUser(val)}
              getOptionLabel={(u) => u.name}
              isOptionEqualToValue={(a, b) => a.id === b.id}
              renderOption={(props, u) => (
                <Box component="li" {...props} key={u.id}>
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {u.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {u.email}
                    </Typography>
                  </Box>
                </Box>
              )}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Usuario"
                  size="small"
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {usersLoading && <CircularProgress size={16} />}
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  }}
                />
              )}
              sx={{ flex: 1, minWidth: 220 }}
              noOptionsText="Sin resultados"
            />

            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>Rol</InputLabel>
              <Select
                value={addRole}
                label="Rol"
                onChange={(e) => setAddRole(e.target.value as StationUserRole)}
              >
                {ASSIGNABLE_ROLES.map((r) => (
                  <MenuItem key={r} value={r}>{ROLE_LABELS[r]}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <Button
              variant="contained"
              startIcon={
                assignMutation.isPending
                  ? <CircularProgress size={16} color="inherit" />
                  : <PersonAddIcon />
              }
              disabled={!selectedUser || assignMutation.isPending}
              onClick={handleAdd}
              sx={{ height: 40, mt: 0.25 }}
            >
              Agregar
            </Button>
          </Box>

          <Divider sx={{ mb: 2 }} />

          {/* Members table */}
          {isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              Error al cargar los miembros. Intenta recargar.
            </Alert>
          )}

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Nombre</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Rol</TableCell>
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

              {!isLoading && members.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} align="center" sx={{ py: 4, color: "text.secondary" }}>
                    No hay miembros registrados
                  </TableCell>
                </TableRow>
              )}

              {!isLoading && members.map((member) => {
                const isOwner = member.role === StationUserRole.owner;
                const isRoleUpdating =
                  updateRoleMutation.isPending &&
                  updateRoleMutation.variables?.memberId === member.id;
                const isRemoving =
                  removeMutation.isPending &&
                  removeMutation.variables === member.id;

                return (
                  <TableRow key={member.id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {member.user_name}
                      </Typography>
                    </TableCell>

                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {member.user_email}
                      </Typography>
                    </TableCell>

                    <TableCell>
                      {isOwner ? (
                        <Chip
                          label={ROLE_LABELS[StationUserRole.owner]}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      ) : (
                        <FormControl size="small" sx={{ minWidth: 160 }}>
                          <Select
                            value={member.role}
                            disabled={isRoleUpdating}
                            onChange={(e) =>
                              handleRoleChange(member, e.target.value as StationUserRole)
                            }
                          >
                            {ASSIGNABLE_ROLES.map((r) => (
                              <MenuItem key={r} value={r}>{ROLE_LABELS[r]}</MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      )}
                    </TableCell>

                    <TableCell align="right">
                      {!isOwner && (
                        <Tooltip title="Eliminar miembro">
                          <span>
                            <IconButton
                              size="small"
                              color="error"
                              disabled={isRemoving}
                              onClick={() => handleRemove(member)}
                            >
                              {isRemoving
                                ? <CircularProgress size={16} color="inherit" />
                                : <DeleteIcon fontSize="small" />}
                            </IconButton>
                          </span>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          {totalMembers > pageSize && (
            <TablePagination
              component="div"
              count={totalMembers}
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
