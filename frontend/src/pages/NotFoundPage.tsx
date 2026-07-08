import { Box, Typography, Button } from "@mui/material";
import { useNavigate } from "react-router-dom";

export default function NotFoundPage() {
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
      <Typography
        variant="h1"
        sx={{ fontFamily: "Space Grotesk", fontWeight: 700, color: "primary.main", fontSize: "6rem" }}
      >
        404
      </Typography>
      <Typography variant="h6" color="text.secondary">
        Página no encontrada
      </Typography>
      <Button variant="contained" onClick={() => navigate("/app/dashboard")}>
        Volver al inicio
      </Button>
    </Box>
  );
}
