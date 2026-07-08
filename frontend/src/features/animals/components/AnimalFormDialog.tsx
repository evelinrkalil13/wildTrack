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
import { useCreateAnimal, useUpdateAnimal } from "../hooks/useAnimalMutations";
import type { AnimalRead } from "../api/animals.types";
import type { ApiError } from "@/api/types/common.types";
import { AnimalSex } from "@/api/types/enums";

const SEX_LABELS: Record<AnimalSex, string> = {
  [AnimalSex.male]:    "Macho",
  [AnimalSex.female]:  "Hembra",
  [AnimalSex.unknown]: "Desconocido",
};

const schema = z.object({
  species:       z.string().min(2, "Mín. 2 caracteres").max(255, "Máx. 255"),
  sex:           z.nativeEnum(AnimalSex),
  rfid_tag:      z.string().max(100, "Máx. 100 caracteres"),
  estimated_age: z.string().max(100, "Máx. 100 caracteres"),
  notes:         z.string(),
});

type FormValues = z.infer<typeof schema>;

const EMPTY: FormValues = {
  species: "", sex: AnimalSex.unknown, rfid_tag: "", estimated_age: "", notes: "",
};

function toFormValues(a: AnimalRead): FormValues {
  return {
    species:       a.species,
    sex:           a.sex,
    rfid_tag:      a.rfid_tag ?? "",
    estimated_age: a.estimated_age ?? "",
    notes:         a.notes ?? "",
  };
}

interface AnimalFormDialogProps {
  open: boolean;
  initialData?: AnimalRead;
  onClose: () => void;
  onSaved: () => void;
}

export default function AnimalFormDialog({
  open,
  initialData,
  onClose,
  onSaved,
}: AnimalFormDialogProps) {
  const isEdit = !!initialData;
  const createMutation = useCreateAnimal();
  const updateMutation = useUpdateAnimal();
  const isPending = createMutation.isPending || updateMutation.isPending;

  const [apiError, setApiError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    control,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (open) {
      reset(initialData ? toFormValues(initialData) : EMPTY);
      setApiError(null);
    }
  }, [open, initialData, reset]);

  function onSubmit(values: FormValues) {
    const handleError = (err: unknown) => {
      const e = err as unknown as ApiError;
      if (e.code === "RFID_TAG_EXISTS") {
        setError("rfid_tag", { message: "Este tag RFID ya está registrado" });
      } else if (e.status === 403) {
        setApiError("No tienes permiso para realizar esta acción");
      } else {
        setApiError(e.message ?? "Error inesperado");
      }
    };

    if (isEdit) {
      updateMutation.mutate(
        {
          id: initialData!.id,
          data: {
            species:       values.species,
            sex:           values.sex,
            rfid_tag:      values.rfid_tag || null,
            estimated_age: values.estimated_age || null,
            notes:         values.notes || null,
          },
        },
        { onSuccess: () => { onSaved(); onClose(); }, onError: handleError }
      );
    } else {
      createMutation.mutate(
        {
          species:       values.species,
          sex:           values.sex,
          rfid_tag:      values.rfid_tag || undefined,
          estimated_age: values.estimated_age || undefined,
          notes:         values.notes || undefined,
        },
        { onSuccess: () => { onSaved(); onClose(); }, onError: handleError }
      );
    }
  }

  return (
    <Dialog open={open} onClose={isPending ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? "Editar animal" : "Registrar animal"}</DialogTitle>

      <DialogContent>
        <Box component="form" id="animal-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          {apiError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setApiError(null)}>
              {apiError}
            </Alert>
          )}

          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12} sm={8}>
              <TextField
                label="Especie"
                fullWidth
                error={!!errors.species}
                helperText={errors.species?.message}
                {...register("species")}
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <Controller
                name="sex"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth error={!!errors.sex}>
                    <InputLabel>Sexo</InputLabel>
                    <Select {...field} label="Sexo">
                      {Object.values(AnimalSex).map((s) => (
                        <MenuItem key={s} value={s}>{SEX_LABELS[s]}</MenuItem>
                      ))}
                    </Select>
                    {errors.sex && (
                      <FormHelperText>{errors.sex.message}</FormHelperText>
                    )}
                  </FormControl>
                )}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Tag RFID (opcional)"
                fullWidth
                inputProps={{ style: { fontFamily: "monospace" } }}
                error={!!errors.rfid_tag}
                helperText={errors.rfid_tag?.message}
                {...register("rfid_tag")}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Edad estimada (opcional)"
                fullWidth
                error={!!errors.estimated_age}
                helperText={errors.estimated_age?.message ?? "Ej: 2 años, adulto, juvenil"}
                {...register("estimated_age")}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                label="Notas (opcional)"
                fullWidth
                multiline
                rows={2}
                error={!!errors.notes}
                helperText={errors.notes?.message}
                {...register("notes")}
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
          form="animal-form"
          variant="contained"
          disabled={isPending}
          startIcon={isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          {isEdit ? "Guardar cambios" : "Registrar"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
