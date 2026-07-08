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
  InputLabel,
  MenuItem,
  Select,
  Typography,
} from "@mui/material";
import { useAssignDevice } from "../hooks/useDeviceMutations";
import type { DeviceRead } from "../api/devices.types";
import type { ApiError } from "@/api/types/common.types";
import { useAllStations } from "@/features/stations/hooks/useStations";

const schema = z.object({
  station_id: z.string().min(1, "Selecciona una estación"),
});

type FormValues = z.infer<typeof schema>;

interface AssignStationDialogProps {
  open: boolean;
  device: DeviceRead | null;
  onClose: () => void;
  onSaved: () => void;
}

export default function AssignStationDialog({
  open,
  device,
  onClose,
  onSaved,
}: AssignStationDialogProps) {
  const assignMutation = useAssignDevice();
  const { data: stations, isLoading: stationsLoading } = useAllStations();
  const [apiError, setApiError] = useState<string | null>(null);

  const { handleSubmit, reset, control, formState: { errors } } =
    useForm<FormValues>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (open) {
      reset({ station_id: "" });
      setApiError(null);
    }
  }, [open, reset]);

  function onSubmit(values: FormValues) {
    if (!device) return;
    assignMutation.mutate(
      { id: device.id, data: { station_id: values.station_id } },
      {
        onSuccess: () => { onSaved(); onClose(); },
        onError: (err) => {
          const e = err as unknown as ApiError;
          setApiError(e.message ?? "Error al asignar el dispositivo");
        },
      }
    );
  }

  return (
    <Dialog open={open} onClose={assignMutation.isPending ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Asignar a estación</DialogTitle>

      <DialogContent>
        {device && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Dispositivo:{" "}
            <Box component="span" sx={{ fontFamily: "monospace", fontWeight: 600 }}>
              {device.serial_number}
            </Box>
          </Typography>
        )}

        <Box component="form" id="assign-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          {apiError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setApiError(null)}>
              {apiError}
            </Alert>
          )}

          {!stationsLoading && (!stations || stations.length === 0) ? (
            <Alert severity="warning">
              No hay estaciones registradas. Crea una estación antes de asignar.
            </Alert>
          ) : (
            <Controller
              name="station_id"
              control={control}
              render={({ field }) => (
                <FormControl fullWidth error={!!errors.station_id}>
                  <InputLabel>Estación</InputLabel>
                  <Select {...field} label="Estación" disabled={stationsLoading}>
                    {(stations ?? []).map((s) => (
                      <MenuItem key={s.id} value={s.id}>
                        {s.code} — {s.name}
                      </MenuItem>
                    ))}
                  </Select>
                  {errors.station_id && (
                    <FormHelperText>{errors.station_id.message}</FormHelperText>
                  )}
                </FormControl>
              )}
            />
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={assignMutation.isPending}>
          Cancelar
        </Button>
        <Button
          type="submit"
          form="assign-form"
          variant="contained"
          disabled={assignMutation.isPending || stationsLoading || !stations?.length}
          startIcon={
            assignMutation.isPending ? <CircularProgress size={16} color="inherit" /> : undefined
          }
        >
          Asignar
        </Button>
      </DialogActions>
    </Dialog>
  );
}
