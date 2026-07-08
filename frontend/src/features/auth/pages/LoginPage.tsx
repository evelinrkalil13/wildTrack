import { useEffect } from "react";
import { useNavigate, useLocation, Link as RouterLink } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Box,
  Button,
  TextField,
  Typography,
  Alert,
  CircularProgress,
  Link,
} from "@mui/material";
import { useLogin } from "../hooks/useLogin";
import { useAuth } from "@/store/auth.context";
import type { ApiError } from "@/api/types/common.types";

const schema = z.object({
  email: z.string().email("Email inválido"),
  password: z.string().min(1, "La contraseña es requerida"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const returnTo =
    (location.state as { returnTo?: string } | null)?.returnTo ?? "/app/dashboard";

  useEffect(() => {
    if (isAuthenticated) navigate(returnTo, { replace: true });
  }, [isAuthenticated, navigate, returnTo]);

  const login = useLogin();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  function onSubmit(data: FormData) {
    login.mutate(data, {
      onSuccess: () => navigate(returnTo, { replace: true }),
    });
  }

  const apiError = login.error as ApiError | null;

  return (
    <Box
      component="form"
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      sx={{ display: "flex", flexDirection: "column", gap: 2 }}
    >
      <Box sx={{ mb: 1 }}>
        <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
          Iniciar sesión
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Ingresa tus credenciales para continuar
        </Typography>
      </Box>

      {apiError && (
        <Alert severity="error" sx={{ borderRadius: 2 }}>
          {apiError.code === "INVALID_CREDENTIALS"
            ? "Credenciales incorrectas. Verifica tu correo y contraseña."
            : apiError.message}
        </Alert>
      )}

      <TextField
        label="Correo electrónico"
        type="email"
        autoComplete="email"
        autoFocus
        error={!!errors.email}
        helperText={errors.email?.message}
        {...register("email")}
      />

      <TextField
        label="Contraseña"
        type="password"
        autoComplete="current-password"
        error={!!errors.password}
        helperText={errors.password?.message}
        {...register("password")}
      />

      <Button
        type="submit"
        variant="contained"
        size="large"
        disabled={login.isPending}
        sx={{ mt: 1, py: 1.2 }}
      >
        {login.isPending ? (
          <CircularProgress size={22} color="inherit" />
        ) : (
          "Entrar"
        )}
      </Button>

      <Typography variant="body2" align="center" color="text.secondary">
        ¿No tienes cuenta?{" "}
        <Link component={RouterLink} to="/auth/register" color="primary">
          Crear cuenta
        </Link>
      </Typography>
    </Box>
  );
}
