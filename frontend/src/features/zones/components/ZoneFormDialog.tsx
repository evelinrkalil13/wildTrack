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
import { useCreateZone } from "../hooks/useZoneMutations";
import { useUpdateZone } from "../hooks/useZoneMutations";
import type { ZoneRead } from "../api/zones.types";
import type { ApiError } from "@/api/types/common.types";

const schema = z.object({
  name:         z.string().min(2, "Mín. 2 caracteres").max(255, "Máx. 255"),
  city:         z.string().min(1, "Requerido").max(255, "Máx. 255"),
  country:      z.string().min(1, "Requerido").max(100, "Máx. 100"),
  municipality: z.string().max(255, "Máx. 255"),
  altitude:     z.string().refine(
    (v) => v === "" || (!isNaN(parseFloat(v)) && isFinite(parseFloat(v))),
    "Número inválido"
  ),
  latitude: z.string()
    .refine((v) => v !== "" && !isNaN(parseFloat(v)), "Requerido")
    .refine((v) => parseFloat(v) >= -90 && parseFloat(v) <= 90, "Entre -90 y 90"),
  longitude: z.string()
    .refine((v) => v !== "" && !isNaN(parseFloat(v)), "Requerido")
    .refine((v) => parseFloat(v) >= -180 && parseFloat(v) <= 180, "Entre -180 y 180"),
});

type FormValues = z.infer<typeof schema>;

const EMPTY: FormValues = {
  name: "", city: "", country: "", municipality: "", altitude: "", latitude: "", longitude: "",
};

function toFormValues(z: ZoneRead): FormValues {
  return {
    name:         z.name,
    city:         z.city,
    country:      z.country,
    municipality: z.municipality ?? "",
    altitude:     z.altitude !== null ? String(z.altitude) : "",
    latitude:     String(z.latitude),
    longitude:    String(z.longitude),
  };
}

interface ZoneFormDialogProps {
  open: boolean;
  initialData?: ZoneRead;
  onClose: () => void;
  onSaved: () => void;
}

export default function ZoneFormDialog({
  open,
  initialData,
  onClose,
  onSaved,
}: ZoneFormDialogProps) {
  const isEdit = !!initialData;
  const createMutation = useCreateZone();
  const updateMutation = useUpdateZone();
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
    const payload = {
      name:         values.name,
      city:         values.city,
      country:      values.country,
      municipality: values.municipality || undefined,
      altitude:     values.altitude ? parseFloat(values.altitude) : undefined,
      latitude:     parseFloat(values.latitude),
      longitude:    parseFloat(values.longitude),
    };

    const handleError = (err: unknown) => {
      const e = err as unknown as ApiError;
      if (e.code === "ZONE_NAME_EXISTS") {
        setError("name", { message: "Ya existe una zona con este nombre en este país" });
      } else {
        setApiError(e.message ?? "Error inesperado");
      }
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
      <DialogTitle>{isEdit ? "Editar zona" : "Nueva zona"}</DialogTitle>

      <DialogContent>
        <Box component="form" id="zone-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          {apiError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setApiError(null)}>
              {apiError}
            </Alert>
          )}

          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12}>
              <TextField
                label="Nombre"
                fullWidth
                error={!!errors.name}
                helperText={errors.name?.message}
                {...register("name")}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Ciudad"
                fullWidth
                error={!!errors.city}
                helperText={errors.city?.message}
                {...register("city")}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="País"
                fullWidth
                error={!!errors.country}
                helperText={errors.country?.message}
                {...register("country")}
              />
            </Grid>

            <Grid item xs={12} sm={8}>
              <TextField
                label="Municipio (opcional)"
                fullWidth
                error={!!errors.municipality}
                helperText={errors.municipality?.message}
                {...register("municipality")}
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                label="Altitud (m)"
                fullWidth
                inputProps={{ inputMode: "decimal" }}
                error={!!errors.altitude}
                helperText={errors.altitude?.message}
                {...register("altitude")}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Latitud"
                fullWidth
                inputProps={{ inputMode: "decimal" }}
                error={!!errors.latitude}
                helperText={errors.latitude?.message ?? "−90 a 90"}
                {...register("latitude")}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Longitud"
                fullWidth
                inputProps={{ inputMode: "decimal" }}
                error={!!errors.longitude}
                helperText={errors.longitude?.message ?? "−180 a 180"}
                {...register("longitude")}
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
          form="zone-form"
          variant="contained"
          disabled={isPending}
          startIcon={isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          {isEdit ? "Guardar cambios" : "Crear zona"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
