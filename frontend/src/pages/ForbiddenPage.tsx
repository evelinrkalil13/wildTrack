import { Box, Typography, Button } from "@mui/material";
import { useNavigate } from "react-router-dom";
import LockIcon from "@mui/icons-material/Lock";

export default function ForbiddenPage() {
  const navigate = useNavigate();
  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
        gap: 2,
      }}
    >
      <LockIcon sx={{ fontSize: 64, color: "error.main", opacity: 0.6 }} />
      <Typography variant="h5" sx={{ fontWeight: 700 }}>
        Acceso denegado
      </Typography>
      <Typography variant="body1" color="text.secondary">
        No tienes permisos para acceder a esta sección.
      </Typography>
      <Button variant="contained" onClick={() => navigate("/app/dashboard")}>
        Volver al dashboard
      </Button>
    </Box>
  );
}
