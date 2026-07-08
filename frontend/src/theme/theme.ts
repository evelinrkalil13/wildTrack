import { createTheme } from "@mui/material/styles";

// Color palette mirrors the Geoportal visual identity (dark forest aesthetic)
export const theme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#52b788",    // --green
      light: "#74c69d",
      dark: "#2d6a4f",    // --forest
    },
    secondary: {
      main: "#e08a1e",    // --amber
      light: "#f6c77a",   // --amber-soft
      dark: "#b86c12",
    },
    error: { main: "#e5554e" },    // --red
    warning: { main: "#e08a1e" },
    success: { main: "#52b788" },
    background: {
      default: "#0f1a15",  // --bg
      paper: "#16241d",    // --surface
    },
    text: {
      primary: "#e8f0ea",  // --ink
      secondary: "#8aa395", // --muted
    },
    divider: "#2a4035",    // --line
  },
  typography: {
    fontFamily: '"Inter", "Roboto", system-ui, sans-serif',
    h1: { fontFamily: '"Space Grotesk", system-ui, sans-serif', fontWeight: 700 },
    h2: { fontFamily: '"Space Grotesk", system-ui, sans-serif', fontWeight: 700 },
    h3: { fontFamily: '"Space Grotesk", system-ui, sans-serif', fontWeight: 600 },
    h4: { fontFamily: '"Space Grotesk", system-ui, sans-serif', fontWeight: 600 },
    h5: { fontFamily: '"Space Grotesk", system-ui, sans-serif', fontWeight: 600 },
    h6: { fontFamily: '"Space Grotesk", system-ui, sans-serif', fontWeight: 500 },
    button: { textTransform: "none", fontWeight: 500 },
  },
  shape: { borderRadius: 8 },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { textTransform: "none", fontWeight: 500, borderRadius: 8 },
        containedPrimary: {
          "&:hover": { backgroundColor: "#43a875" },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: "#16241d",
          backgroundImage: "none",
          borderBottom: "1px solid #2a4035",
          boxShadow: "none",
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: "#16241d",
          backgroundImage: "none",
          borderRight: "1px solid #2a4035",
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          margin: "2px 8px",
          width: "calc(100% - 16px)",
          "&.Mui-selected": {
            backgroundColor: "rgba(82, 183, 136, 0.15)",
            color: "#52b788",
            "& .MuiListItemIcon-root": { color: "#52b788" },
            "&:hover": { backgroundColor: "rgba(82, 183, 136, 0.22)" },
          },
          "&:hover": { backgroundColor: "rgba(255,255,255,0.05)" },
        },
      },
    },
    MuiTextField: {
      defaultProps: { size: "small", variant: "outlined" },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: "none" },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: { borderColor: "#2a4035" },
      },
    },
  },
});
