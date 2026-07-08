import { Chip } from "@mui/material";
import { DeviceStatus } from "@/api/types/enums";

const CONFIG: Record<DeviceStatus, { label: string; color: "success" | "default" | "warning" }> = {
  [DeviceStatus.online]:     { label: "Online",       color: "success"  },
  [DeviceStatus.offline]:    { label: "Offline",      color: "default"  },
  [DeviceStatus.unassigned]: { label: "Sin asignar",  color: "warning"  },
};

interface DeviceStatusChipProps {
  status: DeviceStatus;
}

export default function DeviceStatusChip({ status }: DeviceStatusChipProps) {
  const { label, color } = CONFIG[status] ?? { label: status, color: "default" };
  return <Chip label={label} color={color} size="small" variant="outlined" />;
}
