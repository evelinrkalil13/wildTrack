import { Chip } from "@mui/material";
import { StationStatus } from "@/api/types/enums";

const CONFIG: Record<StationStatus, { label: string; color: "success" | "default" | "warning" | "error" }> = {
  [StationStatus.active]:      { label: "Activa",          color: "success" },
  [StationStatus.inactive]:    { label: "Inactiva",         color: "default" },
  [StationStatus.maintenance]: { label: "Mantenimiento",    color: "warning" },
  [StationStatus.offline]:     { label: "Desconectada",     color: "error"   },
};

interface StationStatusChipProps {
  status: StationStatus;
}

export default function StationStatusChip({ status }: StationStatusChipProps) {
  const { label, color } = CONFIG[status] ?? { label: status, color: "default" };
  return <Chip label={label} color={color} size="small" variant="outlined" />;
}
