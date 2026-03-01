import UploadFileIcon from "@mui/icons-material/UploadFile";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Paper,
  Stack,
  Typography
} from "@mui/material";
import { useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { submitSegmentation } from "../api";

const allowedExtensions = [".nii", ".nii.gz"];

function hasSupportedExtension(fileName: string): boolean {
  const lower = fileName.toLowerCase();
  return allowedExtensions.some((suffix) => lower.endsWith(suffix));
}

export function HomePage() {
  const navigate = useNavigate();

  const [file, setFile] = useState<File | null>(null);
  const [targets, setTargets] = useState<string[]>(["lungs", "liver"]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const targetOptions = useMemo(
    () => [
      { value: "lungs", label: "Lungs" },
      { value: "liver", label: "Liver" }
    ],
    []
  );

  function toggleTarget(target: string) {
    setTargets((prev) => {
      if (prev.includes(target)) {
        return prev.filter((item) => item !== target);
      }
      return [...prev, target];
    });
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!file) {
      setError("Please choose a CT file before running segmentation.");
      return;
    }

    if (!hasSupportedExtension(file.name)) {
      setError("Only .nii or .nii.gz files are supported.");
      return;
    }

    if (targets.length === 0) {
      setError("Select at least one target (lungs or liver).");
      return;
    }

    setSubmitting(true);

    try {
      const response = await submitSegmentation(file, targets, "organ");
      navigate(`/jobs/${response.job_id}`);
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : "Submission failed.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Stack spacing={3}>
      <Paper sx={{ p: 3 }}>
        <Stack spacing={1}>
          <Typography variant="h4" fontWeight={700}>
            CT Organ Segmentation
          </Typography>
          <Typography color="text.secondary">
            Upload a CT NIfTI file, choose targets, and run segmentation. Results include masks, previews, runtime,
            and GPU status.
          </Typography>
        </Stack>
      </Paper>

      <Paper component="form" onSubmit={onSubmit} sx={{ p: 3 }}>
        <Stack spacing={2.5}>
          <Typography variant="h6">1. Upload CT Volume</Typography>
          <Button variant="outlined" component="label" startIcon={<UploadFileIcon />}>
            {file ? file.name : "Choose .nii or .nii.gz file"}
            <input
              hidden
              type="file"
              accept=".nii,.nii.gz"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </Button>

          <Box>
            <Typography variant="h6" gutterBottom>
              2. Select Targets
            </Typography>
            <FormGroup row>
              {targetOptions.map((option) => (
                <FormControlLabel
                  key={option.value}
                  control={
                    <Checkbox
                      checked={targets.includes(option.value)}
                      onChange={() => toggleTarget(option.value)}
                      disabled={submitting}
                    />
                  }
                  label={option.label}
                />
              ))}
            </FormGroup>
          </Box>

          {error && <Alert severity="error">{error}</Alert>}

          <Box>
            <Typography variant="h6" gutterBottom>
              3. Run
            </Typography>
            <Button type="submit" variant="contained" size="large" disabled={submitting}>
              {submitting ? "Submitting..." : "Run Segmentation"}
            </Button>
          </Box>
        </Stack>
      </Paper>
    </Stack>
  );
}
