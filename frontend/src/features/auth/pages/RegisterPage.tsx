import { useNavigate, Link as RouterLink } from "react-router-dom";
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
import { useRegister } from "../hooks/useRegister";
import type { ApiError } from "@/api/types/common.types";

const schema = z
  .object({
    name: z
      .string()
      .min(2, "Mínimo 2 caracteres")
      .max(255, "Máximo 255 caracteres"),
    document: z
      .string()
      .min(5, "Mínimo 5 caracteres")
      .max(50, "Máximo 50 caracteres"),
    email: z.string().email("Email inválido"),
    password: z
      .string()
      .min(8, "Mínimo 8 caracteres")
      .max(128, "Máximo 128 caracteres")
      .regex(/[A-Z]/, "Debe contener al menos una mayúscula")
      .regex(/[a-z]/, "Debe contener al menos una minúscula")
      .regex(/\d/, "Debe contener al menos un número"),
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: "Las contraseñas no coinciden",
    path: ["confirmPassword"],
  });

type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const navigate = useNavigate();
  const register_ = useRegister();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  function onSubmit({ confirmPassword: _, ...data }: FormData) {
    register_.mutate(data, {
      onSuccess: () => {
        navigate("/auth/login", {
          state: { registered: true },
          replace: true,
        });
      },
      onError: (err) => {
        const apiError = err as unknown as ApiError;
        if (apiError.code === "EMAIL_ALREADY_EXISTS") {
          setError("email", { message: "Este correo ya está registrado" });
        }
      },
    });
  }

  const apiError = register_.error as ApiError | null;
  const isGenericError =
    apiError && apiError.code !== "EMAIL_ALREADY_EXISTS";

  return (
    <Box
      component="form"
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      sx={{ display: "flex", flexDirection: "column", gap: 2 }}
    >
      <Box sx={{ mb: 1 }}>
        <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
          Crear cuenta
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Completa los datos para registrarte
        </Typography>
      </Box>

      {isGenericError && (
        <Alert severity="error" sx={{ borderRadius: 2 }}>
          {apiError.message}
        </Alert>
      )}

      <TextField
        label="Nombre completo"
        autoComplete="name"
        autoFocus
        error={!!errors.name}
        helperText={errors.name?.message}
        {...register("name")}
      />

      <TextField
        label="Documento de identidad"
        autoComplete="off"
        error={!!errors.document}
        helperText={errors.document?.message}
        {...register("document")}
      />

      <TextField
        label="Correo electrónico"
        type="email"
        autoComplete="email"
        error={!!errors.email}
        helperText={errors.email?.message}
        {...register("email")}
      />

      <TextField
        label="Contraseña"
        type="password"
        autoComplete="new-password"
        error={!!errors.password}
        helperText={
          errors.password?.message ??
          "Mín. 8 caracteres, una mayúscula, una minúscula y un número"
        }
        {...register("password")}
      />

      <TextField
        label="Confirmar contraseña"
        type="password"
        autoComplete="new-password"
        error={!!errors.confirmPassword}
        helperText={errors.confirmPassword?.message}
        {...register("confirmPassword")}
      />

      <Button
        type="submit"
        variant="contained"
        size="large"
        disabled={register_.isPending}
        sx={{ mt: 1, py: 1.2 }}
      >
        {register_.isPending ? (
          <CircularProgress size={22} color="inherit" />
        ) : (
          "Crear cuenta"
        )}
      </Button>

      <Typography variant="body2" align="center" color="text.secondary">
        ¿Ya tienes cuenta?{" "}
        <Link component={RouterLink} to="/auth/login" color="primary">
          Iniciar sesión
        </Link>
      </Typography>
    </Box>
  );
}
