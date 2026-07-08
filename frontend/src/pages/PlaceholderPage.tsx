import { Box, Typography, Paper } from "@mui/material";
import BuildIcon from "@mui/icons-material/Build";

interface Props {
  title: string;
  slice: string;
}

export default function PlaceholderPage({ title, slice }: Props) {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
        {title}
      </Typography>
      <Paper
        elevation={0}
        sx={{
          p: 4,
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 3,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 2,
          color: "text.secondary",
        }}
      >
        <BuildIcon sx={{ fontSize: 48, opacity: 0.3 }} />
        <Typography variant="body1">
          {title} — se implementa en {slice}
        </Typography>
      </Paper>
    </Box>
  );
}
