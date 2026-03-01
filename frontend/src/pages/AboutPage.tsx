import { Paper, Stack, Typography } from "@mui/material";

export function AboutPage() {
  return (
    <Paper sx={{ p: 3 }}>
      <Stack spacing={1.5}>
        <Typography variant="h4" fontWeight={700}>
          About ASEG
        </Typography>
        <Typography color="text.secondary">
          ASEG is a local lab tool for CT organ segmentation. It currently supports lungs and liver masks using a GPU
          inference pipeline, with async job execution and downloadable outputs.
        </Typography>
        <Typography color="text.secondary">
          This v1 interface is designed for routine lab use and can be extended with additional adapters (for example,
          tumor segmentation) without replacing the API or UI architecture.
        </Typography>
      </Stack>
    </Paper>
  );
}
