import { useQuery } from "@tanstack/react-query";
import {
  Box,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { getFoodStations } from "../api/foods.api";
import type { FoodRead } from "../api/foods.types";

interface FoodStationsDialogProps {
  open: boolean;
  food: FoodRead | null;
  onClose: () => void;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("es-CO", { dateStyle: "medium" });
}

export default function FoodStationsDialog({
  open,
  food,
  onClose,
}: FoodStationsDialogProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["food-stations", food?.id],
    queryFn: () => getFoodStations(food!.id),
    enabled: open && !!food,
    staleTime: 60_000,
  });

  const items = data?.items ?? [];

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ pr: 6 }}>
        Estaciones con "{food?.name}"
        <IconButton
          size="small"
          onClick={onClose}
          sx={{ position: "absolute", top: 12, right: 12 }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ pb: 3 }}>
        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress size={32} />
          </Box>
        )}

        {isError && (
          <Typography color="error" variant="body2" sx={{ py: 2 }}>
            Error al cargar las estaciones asociadas.
          </Typography>
        )}

        {!isLoading && !isError && items.length === 0 && (
          <Typography color="text.secondary" variant="body2" sx={{ py: 2 }}>
            Este alimento no está asignado a ninguna estación.
          </Typography>
        )}

        {!isLoading && !isError && items.length > 0 && (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Código</TableCell>
                <TableCell>Nombre</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell>Asignado</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((s) => (
                <TableRow key={s.station_id} hover>
                  <TableCell>
                    <Typography
                      variant="body2"
                      sx={{ fontFamily: "monospace", fontWeight: 600 }}
                    >
                      {s.station_code}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{s.station_name}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={s.active ? "Activo" : "Inactivo"}
                      color={s.active ? "success" : "default"}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {formatDate(s.created_at)}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DialogContent>
    </Dialog>
  );
}
