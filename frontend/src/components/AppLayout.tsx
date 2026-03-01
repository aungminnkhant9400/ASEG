import { AppBar, Box, Button, Container, Stack, Toolbar, Typography } from "@mui/material";
import { Link as RouterLink, Outlet, useLocation } from "react-router-dom";

function NavButton({ to, label }: { to: string; label: string }) {
  const location = useLocation();
  const active = location.pathname === to;

  return (
    <Button
      component={RouterLink}
      to={to}
      color="inherit"
      variant={active ? "outlined" : "text"}
      sx={{ borderColor: active ? "rgba(255,255,255,0.6)" : "transparent" }}
    >
      {label}
    </Button>
  );
}

export function AppLayout() {
  return (
    <Box sx={{ minHeight: "100vh", backgroundColor: "background.default" }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            ASEG
          </Typography>
          <Stack direction="row" spacing={1}>
            <NavButton to="/" label="Segment" />
            <NavButton to="/about" label="About" />
          </Stack>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Outlet />
      </Container>
    </Box>
  );
}
