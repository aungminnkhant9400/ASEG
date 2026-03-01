import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#0f4c81"
    },
    secondary: {
      main: "#2f7d32"
    },
    background: {
      default: "#f4f7fb"
    }
  },
  typography: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
  },
  shape: {
    borderRadius: 10
  }
});
