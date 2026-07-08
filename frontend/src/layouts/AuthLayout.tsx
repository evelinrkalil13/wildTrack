import { Outlet } from "react-router-dom";
import { Box, Paper, Typography } from "@mui/material";

export default function AuthLayout() {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        backgroundColor: "background.default",
      }}
    >
      {/* Left panel — branding */}
      <Box
        sx={{
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          justifyContent: "center",
          width: 420,
          flexShrink: 0,
          px: 6,
          borderRight: "1px solid",
          borderColor: "divider",
          background:
            "linear-gradient(160deg, #16241d 0%, #0f1a15 100%)",
        }}
      >
        {/* Logo */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 3 }}>
          <Box
            sx={{
              width: 12,
              height: 12,
              borderRadius: "50%",
              bgcolor: "secondary.main",
              boxShadow: "0 0 12px",
              boxShadowColor: "secondary.main",
            }}
          />
          <Typography
            variant="h4"
            sx={{ fontFamily: "Space Grotesk", fontWeight: 700 }}
          >
            WildTrack
          </Typography>
        </Box>

        <Typography
          variant="body1"
          color="text.secondary"
          sx={{ mb: 4, lineHeight: 1.8 }}
        >
          Plataforma IoT para el monitoreo inteligente de fauna silvestre.
          Seguimiento por RFID, estaciones de alimentación y análisis
          geoespacial en tiempo real.
        </Typography>

        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          {["📡 IoT", "🗺️ SIG", "🐾 RFID", "📊 Analytics"].map((chip) => (
            <Box
              key={chip}
              sx={{
                px: 1.5,
                py: 0.5,
                borderRadius: 2,
                border: "1px solid",
                borderColor: "divider",
                fontSize: "0.78rem",
                color: "text.secondary",
              }}
            >
              {chip}
            </Box>
          ))}
        </Box>
      </Box>

      {/* Right panel — form */}
      <Box
        sx={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          p: 3,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            width: "100%",
            maxWidth: 420,
            p: { xs: 3, sm: 4 },
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 3,
          }}
        >
          <Outlet />
        </Paper>
      </Box>
    </Box>
  );
}
