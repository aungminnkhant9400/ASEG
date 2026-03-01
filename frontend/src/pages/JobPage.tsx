import { Alert, Button, Snackbar, Stack } from "@mui/material";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";

import { fetchJob } from "../api";
import { JobDetails } from "../components/JobDetails";
import type { JobData } from "../types";

const POLL_MS = 2000;

export function JobPage() {
  const { jobId = "" } = useParams<{ jobId: string }>();

  const [job, setJob] = useState<JobData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [debug, setDebug] = useState(false);
  const [copyOpen, setCopyOpen] = useState(false);

  const isTerminal = useMemo(() => job?.status === "completed" || job?.status === "failed", [job?.status]);

  const loadJob = useCallback(async () => {
    if (!jobId) {
      setLoadError("Job id is missing.");
      setLoading(false);
      return;
    }

    try {
      const next = await fetchJob(jobId);
      setJob(next);
      setLoadError("");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load job.";
      setLoadError(message);
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    setLoading(true);
    void loadJob();
  }, [loadJob]);

  useEffect(() => {
    if (!jobId || isTerminal) {
      return;
    }

    const timer = window.setInterval(() => {
      void loadJob();
    }, POLL_MS);

    return () => window.clearInterval(timer);
  }, [jobId, isTerminal, loadJob]);

  async function handleCopyLink() {
    if (!jobId) {
      return;
    }

    const shareUrl = `${window.location.origin}/jobs/${jobId}`;

    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopyOpen(true);
    } catch {
      setLoadError("Could not copy the results link. Copy it manually from the browser URL bar.");
    }
  }

  return (
    <Stack spacing={2.5}>
      <Stack direction="row" spacing={1.5}>
        <Button component={RouterLink} to="/" variant="outlined">
          New Segmentation
        </Button>
        <Button component={RouterLink} to="/about" variant="text">
          About ASEG
        </Button>
      </Stack>

      <JobDetails
        job={job}
        loading={loading}
        loadError={loadError}
        debug={debug}
        onDebugChange={setDebug}
        onCopyLink={handleCopyLink}
      />

      <Snackbar open={copyOpen} autoHideDuration={2200} onClose={() => setCopyOpen(false)}>
        <Alert severity="success" sx={{ width: "100%" }} onClose={() => setCopyOpen(false)}>
          Results link copied.
        </Alert>
      </Snackbar>
    </Stack>
  );
}
