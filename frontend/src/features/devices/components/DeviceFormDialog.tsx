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
import { useCreateDevice } from "../hooks/useDeviceMutations";
import { useUpdateDevice } from "../hooks/useDeviceMutations";
import type { DeviceRead } from "../api/devices.types";
import type { ApiError } from "@/api/types/common.types";

const MAC_REGEX = /^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/;

const baseSchema = z.object({
  serial_number: z.string(),
  name:          z.string().max(255, "Máx. 255 caracteres"),
  mac_address:   z.string(),
});

const createSchema = baseSchema.extend({
  serial_number: z.string().min(3, "Mín. 3 caracteres").max(100, "Máx. 100"),
  mac_address:   z.string().refine(
    (v) => v === "" || MAC_REGEX.test(v),
    "Formato: AA:BB:CC:DD:EE:FF"
  ),
});

const editSchema = baseSchema;

type FormValues = z.infer<typeof createSchema>;

const EMPTY: FormValues = { serial_number: "", name: "", mac_address: "" };

function toFormValues(d: DeviceRead): FormValues {
  return {
    serial_number: d.serial_number,
    name:          d.name ?? "",
    mac_address:   d.mac_address ?? "",
  };
}

interface DeviceFormDialogProps {
  open: boolean;
  initialData?: DeviceRead;
  onClose: () => void;
  onSaved: () => void;
}

export default function DeviceFormDialog({
  open,
  initialData,
  onClose,
  onSaved,
}: DeviceFormDialogProps) {
  const isEdit = !!initialData;
  const createMutation = useCreateDevice();
  const updateMutation = useUpdateDevice();
  const isPending = createMutation.isPending || updateMutation.isPending;

  const [apiError, setApiError] = useState<string | null>(null);

  const schema = isEdit ? editSchema : createSchema;
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
      if (e.code === "SERIAL_EXISTS") {
        setError("serial_number", { message: "Este número de serie ya existe" });
      } else {
        setApiError(e.message ?? "Error inesperado");
      }
    };

    if (isEdit) {
      updateMutation.mutate(
        { id: initialData!.id, data: { name: values.name || undefined } },
        { onSuccess: () => { onSaved(); onClose(); }, onError: handleError }
      );
    } else {
      createMutation.mutate(
        {
          serial_number: values.serial_number,
          name:          values.name || undefined,
          mac_address:   values.mac_address || undefined,
        },
        { onSuccess: () => { onSaved(); onClose(); }, onError: handleError }
      );
    }
  }

  return (
    <Dialog open={open} onClose={isPending ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? "Editar dispositivo" : "Nuevo dispositivo"}</DialogTitle>

      <DialogContent>
        <Box component="form" id="device-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          {apiError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setApiError(null)}>
              {apiError}
            </Alert>
          )}

          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12}>
              <TextField
                label="Número de serie"
                fullWidth
                disabled={isEdit}
                inputProps={{ style: { fontFamily: "monospace" } }}
                error={!!errors.serial_number}
                helperText={errors.serial_number?.message ?? "Identificador único del dispositivo"}
                {...register("serial_number")}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                label="Nombre (opcional)"
                fullWidth
                error={!!errors.name}
                helperText={errors.name?.message}
                {...register("name")}
              />
            </Grid>

            {!isEdit && (
              <Grid item xs={12}>
                <TextField
                  label="Dirección MAC (opcional)"
                  fullWidth
                  inputProps={{ style: { fontFamily: "monospace" } }}
                  error={!!errors.mac_address}
                  helperText={errors.mac_address?.message ?? "Ej: AA:BB:CC:DD:EE:FF"}
                  {...register("mac_address")}
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
          form="device-form"
          variant="contained"
          disabled={isPending}
          startIcon={isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          {isEdit ? "Guardar cambios" : "Crear dispositivo"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
