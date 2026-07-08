import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
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
  FormControl,
  FormHelperText,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  TextField,
} from "@mui/material";
import { useCreateStation } from "../hooks/useStationMutations";
import { useUpdateStation } from "../hooks/useStationMutations";
import type { StationRead } from "../api/stations.types";
import type { ApiError } from "@/api/types/common.types";
import { StationStatus } from "@/api/types/enums";
import { useAllZones } from "@/features/zones/hooks/useZones";

const STATUS_LABELS: Record<StationStatus, string> = {
  [StationStatus.active]:      "Activa",
  [StationStatus.inactive]:    "Inactiva",
  [StationStatus.maintenance]: "Mantenimiento",
  [StationStatus.offline]:     "Desconectada",
};

const createSchema = z.object({
  code: z.string()
    .min(2, "Mín. 2 caracteres")
    .max(50, "Máx. 50 caracteres")
    .regex(/^[A-Z0-9\-]{2,50}$/, "Solo mayúsculas, números y guiones"),
  name: z.string().min(2, "Mín. 2 caracteres").max(255, "Máx. 255"),
  zone_id: z.string().min(1, "Selecciona una zona"),
  latitude: z.string()
    .refine((v) => v !== "" && !isNaN(parseFloat(v)), "Requerido")
    .refine((v) => parseFloat(v) >= -90 && parseFloat(v) <= 90, "Entre -90 y 90"),
  longitude: z.string()
    .refine((v) => v !== "" && !isNaN(parseFloat(v)), "Requerido")
    .refine((v) => parseFloat(v) >= -180 && parseFloat(v) <= 180, "Entre -180 y 180"),
});

const editSchema = createSchema.extend({
  status: z.nativeEnum(StationStatus),
});

type CreateValues = z.infer<typeof createSchema>;
type EditValues = z.infer<typeof editSchema>;
type FormValues = EditValues;

const EMPTY: FormValues = {
  code: "", name: "", zone_id: "", latitude: "", longitude: "",
  status: StationStatus.active,
};

function toFormValues(s: StationRead): FormValues {
  return {
    code:      s.code,
    name:      s.name,
    zone_id:   s.zone_id,
    latitude:  String(s.latitude),
    longitude: String(s.longitude),
    status:    s.status,
  };
}

interface StationFormDialogProps {
  open: boolean;
  initialData?: StationRead;
  onClose: () => void;
  onSaved: () => void;
}

export default function StationFormDialog({
  open,
  initialData,
  onClose,
  onSaved,
}: StationFormDialogProps) {
  const isEdit = !!initialData;
  const createMutation = useCreateStation();
  const updateMutation = useUpdateStation();
  const isPending = createMutation.isPending || updateMutation.isPending;

  const { data: zones, isLoading: zonesLoading } = useAllZones();
  const [apiError, setApiError] = useState<string | null>(null);

  const schema = isEdit ? editSchema : createSchema;
  const { register, handleSubmit, reset, setError, control, formState: { errors } } =
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
      if (e.code === "STATION_CODE_EXISTS") {
        setError("code", { message: "Este código ya está en uso" });
      } else {
        setApiError(e.message ?? "Error inesperado");
      }
    };

    if (isEdit) {
      updateMutation.mutate(
        {
          id: initialData!.id,
          data: {
            name:      values.name,
            status:    values.status,
            zone_id:   values.zone_id,
            latitude:  parseFloat(values.latitude),
            longitude: parseFloat(values.longitude),
          },
        },
        { onSuccess: () => { onSaved(); onClose(); }, onError: handleError }
      );
    } else {
      const cv = values as CreateValues;
      createMutation.mutate(
        {
          code:      cv.code,
          name:      cv.name,
          zone_id:   cv.zone_id,
          latitude:  parseFloat(cv.latitude),
          longitude: parseFloat(cv.longitude),
        },
        { onSuccess: () => { onSaved(); onClose(); }, onError: handleError }
      );
    }
  }

  return (
    <Dialog open={open} onClose={isPending ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? "Editar estación" : "Nueva estación"}</DialogTitle>

      <DialogContent>
        <Box component="form" id="station-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          {apiError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setApiError(null)}>
              {apiError}
            </Alert>
          )}

          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12} sm={5}>
              <TextField
                label="Código"
                fullWidth
                disabled={isEdit}
                inputProps={{ style: { fontFamily: "monospace" } }}
                error={!!errors.code}
                helperText={errors.code?.message ?? "Ej: WT-001"}
                {...register("code")}
              />
            </Grid>

            <Grid item xs={12} sm={7}>
              <TextField
                label="Nombre"
                fullWidth
                error={!!errors.name}
                helperText={errors.name?.message}
                {...register("name")}
              />
            </Grid>

            <Grid item xs={12}>
              <Controller
                name="zone_id"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth error={!!errors.zone_id}>
                    <InputLabel>Zona</InputLabel>
                    <Select {...field} label="Zona" disabled={zonesLoading}>
                      {(zones ?? []).map((z) => (
                        <MenuItem key={z.id} value={z.id}>
                          {z.name} — {z.city}
                        </MenuItem>
                      ))}
                    </Select>
                    {errors.zone_id && (
                      <FormHelperText>{errors.zone_id.message}</FormHelperText>
                    )}
                  </FormControl>
                )}
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

            {isEdit && (
              <Grid item xs={12}>
                <Controller
                  name="status"
                  control={control}
                  render={({ field }) => (
                    <FormControl fullWidth error={!!errors.status}>
                      <InputLabel>Estado</InputLabel>
                      <Select {...field} label="Estado">
                        {Object.values(StationStatus).map((s) => (
                          <MenuItem key={s} value={s}>
                            {STATUS_LABELS[s]}
                          </MenuItem>
                        ))}
                      </Select>
                      {errors.status && (
                        <FormHelperText>{errors.status.message}</FormHelperText>
                      )}
                    </FormControl>
                  )}
                />
              </Grid>
            )}
          </Grid>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={isPending}>
          Cancelar
        </Button>
        <Button
          type="submit"
          form="station-form"
          variant="contained"
          disabled={isPending}
          startIcon={isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          {isEdit ? "Guardar cambios" : "Crear estación"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
