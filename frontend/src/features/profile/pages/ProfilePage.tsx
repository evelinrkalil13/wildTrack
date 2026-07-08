import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Snackbar,
  TextField,
  Typography,
} from "@mui/material";
import PersonIcon from "@mui/icons-material/Person";
import LockIcon from "@mui/icons-material/Lock";
import { useAuth } from "@/store/auth.context";
import { useUpdateProfile, useChangePassword } from "../hooks/useProfileMutations";
import type { ApiError } from "@/api/types/common.types";

const nameSchema = z.object({
  name: z.string().trim().min(2, "Mín. 2 caracteres").max(255, "Máx. 255"),
});

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Requerido"),
    new_password: z
      .string()
      .min(8, "Mín. 8 caracteres")
      .max(128, "Máx. 128")
      .regex(/[A-Z]/, "Debe tener al menos una mayúscula")
      .regex(/[a-z]/, "Debe tener al menos una minúscula")
      .regex(/\d/, "Debe tener al menos un número"),
    confirm_password: z.string(),
  })
  .refine((v) => v.new_password === v.confirm_password, {
    message: "Las contraseñas no coinciden",
    path: ["confirm_password"],
  });

type NameValues = z.infer<typeof nameSchema>;
type PasswordValues = z.infer<typeof passwordSchema>;

interface SnackState { open: boolean; message: string; severity: "success" | "error" }

function errorMessage(err: unknown): string {
  const e = err as ApiError;
  if (e?.code === "INVALID_CURRENT_PASSWORD") return "La contraseña actual es incorrecta";
  return e?.message ?? "Ocurrió un error";
}

export default function ProfilePage() {
  const { user, token, setAuth } = useAuth();
  const [snack, setSnack] = useState<SnackState>({ open: false, message: "", severity: "success" });

  const updateMutation = useUpdateProfile();
  const passwordMutation = useChangePassword();

  const nameForm = useForm<NameValues>({
    resolver: zodResolver(nameSchema),
    defaultValues: { name: user?.name ?? "" },
  });

  const passwordForm = useForm<PasswordValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  function showSnack(message: string, severity: "success" | "error") {
    setSnack({ open: true, message, severity });
  }

  function handleNameSubmit(values: NameValues) {
    updateMutation.mutate(values, {
      onSuccess: (result) => {
        setAuth(token!, { ...user!, name: result.name });
        showSnack("Nombre actualizado", "success");
      },
      onError: (err) => showSnack(errorMessage(err), "error"),
    });
  }

  function handlePasswordSubmit(values: PasswordValues) {
    passwordMutation.mutate(
      { current_password: values.current_password, new_password: values.new_password },
      {
        onSuccess: () => {
          passwordForm.reset();
          showSnack("Contraseña actualizada", "success");
        },
        onError: (err) => showSnack(errorMessage(err), "error"),
      }
    );
  }

  return (
    <Box sx={{ p: 3, maxWidth: 560 }}>
      <Typography variant="h5" fontWeight={700} mb={3}>
        Mi perfil
      </Typography>

      {/* Card 1 — Edit name */}
      <Card sx={{ mb: 3, bgcolor: "background.paper" }}>
        <CardContent>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
            <PersonIcon fontSize="small" color="primary" />
            <Typography variant="subtitle1" fontWeight={600}>
              Información personal
            </Typography>
          </Box>

          <Typography variant="body2" color="text.secondary" mb={2}>
            {user?.email}
          </Typography>

          <Box
            component="form"
            onSubmit={nameForm.handleSubmit(handleNameSubmit)}
            sx={{ display: "flex", flexDirection: "column", gap: 2 }}
          >
            <TextField
              label="Nombre"
              fullWidth
              size="small"
              {...nameForm.register("name")}
              error={!!nameForm.formState.errors.name}
              helperText={nameForm.formState.errors.name?.message}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={updateMutation.isPending}
              startIcon={updateMutation.isPending ? <CircularProgress size={16} /> : undefined}
              sx={{ alignSelf: "flex-end" }}
            >
              Guardar
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Card 2 — Change password */}
      <Card sx={{ bgcolor: "background.paper" }}>
        <CardContent>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
            <LockIcon fontSize="small" color="primary" />
            <Typography variant="subtitle1" fontWeight={600}>
              Cambiar contraseña
            </Typography>
          </Box>

          <Box
            component="form"
            onSubmit={passwordForm.handleSubmit(handlePasswordSubmit)}
            sx={{ display: "flex", flexDirection: "column", gap: 2 }}
          >
            <TextField
              label="Contraseña actual"
              type="password"
              fullWidth
              size="small"
              {...passwordForm.register("current_password")}
              error={!!passwordForm.formState.errors.current_password}
              helperText={passwordForm.formState.errors.current_password?.message}
            />
            <TextField
              label="Nueva contraseña"
              type="password"
              fullWidth
              size="small"
              {...passwordForm.register("new_password")}
              error={!!passwordForm.formState.errors.new_password}
              helperText={passwordForm.formState.errors.new_password?.message}
            />
            <TextField
              label="Confirmar contraseña"
              type="password"
              fullWidth
              size="small"
              {...passwordForm.register("confirm_password")}
              error={!!passwordForm.formState.errors.confirm_password}
              helperText={passwordForm.formState.errors.confirm_password?.message}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={passwordMutation.isPending}
              startIcon={passwordMutation.isPending ? <CircularProgress size={16} /> : undefined}
              sx={{ alignSelf: "flex-end" }}
            >
              Cambiar contraseña
            </Button>
          </Box>
        </CardContent>
      </Card>

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
