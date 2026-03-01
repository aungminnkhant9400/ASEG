import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  FormControlLabel,
  IconButton,
  Paper,
  Stack,
  Switch,
  Tooltip,
  Typography
} from "@mui/material";
import { useMemo } from "react";

import { toFileUrl } from "../api";
import type { JobData, JobStatus } from "../types";

interface JobDetailsProps {
  job: JobData | null;
  loading: boolean;
  loadError: string;
  debug: boolean;
  onDebugChange: (value: boolean) => void;
  onCopyLink: () => void;
}

const statusColorMap: Record<JobStatus, "default" | "info" | "warning" | "success" | "error"> = {
  pending: "warning",
  running: "info",
  completed: "success",
  failed: "error"
};

const metricGridStyles = {
  display: "grid",
  gap: 2,
  gridTemplateColumns: {
    xs: "1fr",
    sm: "repeat(2, minmax(0, 1fr))",
    md: "repeat(4, minmax(0, 1fr))"
  }
};

const gpuGridStyles = {
  display: "grid",
  gap: 2,
  gridTemplateColumns: {
    xs: "1fr",
    sm: "repeat(2, minmax(0, 1fr))",
    md: "repeat(3, minmax(0, 1fr))"
  }
};

const previewGridStyles = {
  display: "grid",
  gap: 2,
  gridTemplateColumns: {
    xs: "1fr",
    md: "repeat(3, minmax(0, 1fr))"
  }
};

const previewPlaneLabels = ["Axial", "Sagittal", "Coronal"];

function LabelValue({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography sx={{ wordBreak: "break-word" }}>{value}</Typography>
    </Box>
  );
}

export function JobDetails({
  job,
  loading,
  loadError,
  debug,
  onDebugChange,
  onCopyLink
}: JobDetailsProps) {
  const previewUrls = useMemo(() => {
    if (!job) {
      return [] as string[];
    }
    return (job.outputs?.previews ?? [])
      .map((path) => toFileUrl(path))
      .filter((url): url is string => Boolean(url));
  }, [job]);

  const lungsUrl = toFileUrl(job?.outputs?.masks?.lungs ?? null);
  const liverUrl = toFileUrl(job?.outputs?.masks?.liver ?? null);

  return (
    <Stack spacing={2.5}>
      <Paper sx={{ p: 2.5 }}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={2}
          justifyContent="space-between"
          alignItems={{ sm: "center" }}
        >
          <Box>
            <Typography variant="h5" fontWeight={700}>
              Segmentation Result
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Job ID: {job?.job_id ?? "-"}
            </Typography>
          </Box>

          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            {job && <Chip label={job.status.toUpperCase()} color={statusColorMap[job.status]} />}
            <Tooltip title="Copy share link">
              <span>
                <IconButton color="primary" onClick={onCopyLink} disabled={!job}>
                  <ContentCopyIcon />
                </IconButton>
              </span>
            </Tooltip>
            <FormControlLabel
              control={<Switch checked={debug} onChange={(event) => onDebugChange(event.target.checked)} />}
              label="Debug"
            />
          </Stack>
        </Stack>
      </Paper>

      {loading && (
        <Paper sx={{ p: 3 }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <CircularProgress size={24} />
            <Typography>Checking job status...</Typography>
          </Stack>
        </Paper>
      )}

      {loadError && <Alert severity="error">{loadError}</Alert>}

      {job && job.error && job.status === "failed" && <Alert severity="error">{job.error}</Alert>}

      {job && (
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="h6" gutterBottom>
            Status Summary
          </Typography>
          <Box sx={metricGridStyles}>
            <LabelValue label="Created" value={new Date(job.created_at).toLocaleString()} />
            <LabelValue label="Started" value={job.started_at ? new Date(job.started_at).toLocaleString() : "-"} />
            <LabelValue
              label="Completed"
              value={job.completed_at ? new Date(job.completed_at).toLocaleString() : "-"}
            />
            <LabelValue
              label="Runtime"
              value={job.runtime_sec !== null ? `${job.runtime_sec.toFixed(2)} sec` : "-"}
            />
          </Box>
        </Paper>
      )}

      {job && (
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="h6" gutterBottom>
            GPU Metrics
          </Typography>
          <Box sx={gpuGridStyles}>
            <LabelValue label="GPU Name" value={job.gpu.name ?? "Not available"} />
            <LabelValue label="GPU UUID" value={job.gpu.uuid ?? "Not available"} />
            <LabelValue
              label="Utilization"
              value={job.gpu.utilization_pct !== null ? `${job.gpu.utilization_pct}%` : "-"}
            />
            <LabelValue
              label="Memory"
              value={
                job.gpu.mem_used_mb !== null && job.gpu.mem_total_mb !== null
                  ? `${job.gpu.mem_used_mb} / ${job.gpu.mem_total_mb} MB`
                  : "-"
              }
            />
            <LabelValue
              label="Temperature"
              value={job.gpu.temperature_c !== null ? `${job.gpu.temperature_c} C` : "-"}
            />
          </Box>
        </Paper>
      )}

      {job && job.status === "completed" && (
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="h6" gutterBottom>
            Preview Overlays
          </Typography>
          <Box sx={previewGridStyles}>
            {previewUrls.length === 0 && <Alert severity="info">No preview images were generated.</Alert>}
            {previewUrls.map((url, index) => (
              <Paper key={url} variant="outlined" sx={{ p: 1.25 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  {previewPlaneLabels[index] ?? `Slice ${index + 1}`}
                </Typography>
                <Box
                  component="img"
                  src={url}
                  alt={`${previewPlaneLabels[index] ?? `Slice ${index + 1}`} overlay`}
                  sx={{ width: "100%", borderRadius: 1, border: "1px solid #ddd" }}
                />
              </Paper>
            ))}
          </Box>

          <Divider sx={{ my: 2 }} />

          <Typography variant="h6" gutterBottom>
            Downloads
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} flexWrap="wrap">
            {lungsUrl && (
              <Button variant="contained" component="a" href={lungsUrl}>
                Download Lungs Mask
              </Button>
            )}
            {liverUrl && (
              <Button variant="contained" component="a" href={liverUrl}>
                Download Liver Mask
              </Button>
            )}
            {previewUrls.map((url, index) => (
              <Button key={url} variant="outlined" component="a" href={url}>
                Download {previewPlaneLabels[index] ?? `Overlay ${index + 1}`}
              </Button>
            ))}
          </Stack>
        </Paper>
      )}

      {debug && job && (
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="h6" gutterBottom>
            Raw Job JSON
          </Typography>
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 1.5,
              backgroundColor: "#111827",
              color: "#e5e7eb",
              borderRadius: 1,
              overflowX: "auto",
              fontSize: "0.85rem"
            }}
          >
            {JSON.stringify(job, null, 2)}
          </Box>
        </Paper>
      )}
    </Stack>
  );
}
