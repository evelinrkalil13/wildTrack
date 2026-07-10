import type { ReactNode } from "react";
import { Box, Paper, Skeleton, Tooltip, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

interface StatCardProps {
  label: string;
  sublabel?: string;
  value?: number;
  stringValue?: string;
  icon: ReactNode;
  paletteColor?: "primary" | "success" | "warning" | "error" | "info" | "secondary";
  loading: boolean;
  error?: boolean;
  placeholder?: boolean;
}

export default function StatCard({
  label,
  sublabel,
  value,
  stringValue,
  icon,
  paletteColor = "primary",
  loading,
  error = false,
  placeholder = false,
}: StatCardProps) {
  const displayValue =
    placeholder || error
      ? "—"
      : stringValue ?? value?.toLocaleString() ?? "—";

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 3,
        display: "flex",
        alignItems: "flex-start",
        gap: 2,
        opacity: placeholder ? 0.5 : 1,
        height: "100%",
      }}
    >
      <Box
        sx={{
          width: 44,
          height: 44,
          borderRadius: 2,
          bgcolor: (theme) =>
            placeholder
              ? theme.palette.action.disabledBackground
              : alpha(theme.palette[paletteColor].main, 0.15),
          color: placeholder ? "text.disabled" : `${paletteColor}.main`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        {placeholder ? <HelpOutlineIcon fontSize="small" /> : icon}
      </Box>

      <Box sx={{ minWidth: 0 }}>
        <Typography variant="body2" color="text.secondary" noWrap>
          {label}
        </Typography>

        {loading ? (
          <Skeleton variant="text" width={56} height={40} />
        ) : (
          <Tooltip title={error ? "Error al cargar" : ""} placement="top">
            <Typography
              variant="h5"
              sx={{ fontWeight: 700, lineHeight: 1.2, mt: 0.25 }}
              color={error || placeholder ? "text.disabled" : "text.primary"}
            >
              {displayValue}
            </Typography>
          </Tooltip>
        )}

        {sublabel && (
          <Typography variant="caption" color="text.secondary">
            {sublabel}
          </Typography>
        )}
      </Box>
    </Paper>
  );
}
