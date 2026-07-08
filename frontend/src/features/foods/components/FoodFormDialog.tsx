import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  TextField,
} from "@mui/material";
import { useCreateFood, useUpdateFood } from "../hooks/useFoodMutations";
import type { FoodRead } from "../api/foods.types";
import type { ApiError } from "@/api/types/common.types";

const schema = z.object({
  name:        z.string().min(2, "Mín. 2 caracteres").max(255, "Máx. 255"),
  type:        z.string().min(1, "Requerido").max(100, "Máx. 100"),
  description: z.string(),
});

type FormValues = z.infer<typeof schema>;

const EMPTY: FormValues = { name: "", type: "", description: "" };

function toFormValues(f: FoodRead): FormValues {
  return {
    name:        f.name,
    type:        f.type,
    description: f.description ?? "",
  };
}

interface FoodFormDialogProps {
  open: boolean;
  initialData?: FoodRead;
  onClose: () => void;
  onSaved: () => void;
}

export default function FoodFormDialog({
  open,
  initialData,
  onClose,
  onSaved,
}: FoodFormDialogProps) {
  const isEdit = !!initialData;
  const createMutation = useCreateFood();
  const updateMutation = useUpdateFood();
  const isPending = createMutation.isPending || updateMutation.isPending;

  const [apiError, setApiError] = useState<string | null>(null);

  const { register, handleSubmit, reset, setError, formState: { errors } } =
    useForm<FormValues>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (open) {
      reset(initialData ? toFormValues(initialData) : EMPTY);
      setApiError(null);
    }
  }, [open, initialData, reset]);

  function onSubmit(values: FormValues) {
    const handleError = (err: unknown) => {
      const e = err as unknown as ApiError;
      if (e.code === "FOOD_NAME_EXISTS") {
        setError("name", { message: "Ya existe un alimento con este nombre" });
      } else if (e.status === 403) {
        setApiError("No tienes permiso para realizar esta acción");
      } else {
        setApiError(e.message ?? "Error inesperado");
      }
    };

    const payload = {
      name:        values.name,
      type:        values.type,
      description: values.description || undefined,
    };

    if (isEdit) {
      updateMutation.mutate(
        { id: initialData!.id, data: payload },
        { onSuccess: () => { onSaved(); onClose(); }, onError: handleError }
      );
    } else {
      createMutation.mutate(payload, {
        onSuccess: () => { onSaved(); onClose(); },
        onError: handleError,
      });
    }
  }

  return (
    <Dialog open={open} onClose={isPending ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? "Editar alimento" : "Nuevo alimento"}</DialogTitle>

      <DialogContent>
        <Box component="form" id="food-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          {apiError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setApiError(null)}>
              {apiError}
            </Alert>
          )}

          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12} sm={7}>
              <TextField
                label="Nombre"
                fullWidth
                error={!!errors.name}
                helperText={errors.name?.message}
                {...register("name")}
              />
            </Grid>

            <Grid item xs={12} sm={5}>
              <TextField
                label="Tipo"
                fullWidth
                error={!!errors.type}
                helperText={errors.type?.message ?? "Ej: semillas, frutas, pellets"}
                {...register("type")}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                label="Descripción (opcional)"
                fullWidth
                multiline
                rows={2}
                error={!!errors.description}
                helperText={errors.description?.message}
                {...register("description")}
              />
            </Grid>
          </Grid>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={isPending}>
          Cancelar
        </Button>
        <Button
          type="submit"
          form="food-form"
          variant="contained"
          disabled={isPending}
          startIcon={isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          {isEdit ? "Guardar cambios" : "Crear alimento"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
