import { useState } from "react";
import { Box, IconButton, Typography } from "@mui/material";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import CloseIcon from "@mui/icons-material/Close";

export default function GeoportalLegend() {
  const [open, setOpen] = useState(false);

  return (
    <Box
      sx={{
        position: "absolute",
        bottom: 32,
        left: 12,
        zIndex: 1000,
      }}
    >
      {!open ? (
        <IconButton
          size="small"
          onClick={() => setOpen(true)}
          sx={{
            bgcolor: "background.paper",
            border: "1px solid",
            borderColor: "divider",
            boxShadow: 2,
            "&:hover": { bgcolor: "action.hover" },
          }}
          title="Cómo leer el mapa"
        >
          <InfoOutlinedIcon fontSize="small" />
        </IconButton>
      ) : (
        <Box
          sx={{
            bgcolor: "background.paper",
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 2,
            p: 1.5,
            minWidth: 200,
            boxShadow: 4,
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              mb: 1,
            }}
          >
            <Typography
              variant="caption"
              sx={{ fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5 }}
            >
              Cómo leer el mapa
            </Typography>
            <IconButton size="small" onClick={() => setOpen(false)} sx={{ p: 0.25 }}>
              <CloseIcon sx={{ fontSize: 14 }} />
            </IconButton>
          </Box>

          {[
            { icon: "⬤", label: "Tamaño = nº de visitas", color: "#52b788" },
            { icon: "◔", label: "Arco ámbar = % sin identificar", color: "#e08a1e" },
            { icon: "⬤", label: "Gris = sin actividad / offline", color: "#5f7669" },
            { icon: "⬤", label: "Amarillo = en alerta", color: "#e08a1e" },
            { icon: "◉", label: "Anillo azul = en línea ahora", color: "#3b82f6" },
          ].map(({ icon, label, color }) => (
            <Box
              key={label}
              sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}
            >
              <Typography sx={{ fontSize: 12, color, lineHeight: 1, width: 14 }}>
                {icon}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {label}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
