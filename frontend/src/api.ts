import type { JobData, SegmentSubmitResponse } from "./types";

function parseErrorText(text: string): string {
  if (!text) {
    return "Unknown error";
  }

  try {
    const parsed = JSON.parse(text) as { detail?: string };
    if (parsed.detail) {
      return parsed.detail;
    }
  } catch {
    // Ignore and return raw text
  }

  return text;
}

export async function submitSegmentation(
  file: File,
  targets: string[],
  task = "organ"
): Promise<SegmentSubmitResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("task", task);
  formData.append("targets", JSON.stringify(targets));

  const response = await fetch("/segment", {
    method: "POST",
    body: formData
  });

  const text = await response.text();
  if (!response.ok) {
    throw new Error(parseErrorText(text));
  }

  return JSON.parse(text) as SegmentSubmitResponse;
}

export async function fetchJob(jobId: string): Promise<JobData> {
  const response = await fetch(`/jobs/${jobId}`, {
    headers: {
      Accept: "application/json"
    }
  });

  const text = await response.text();
  if (!response.ok) {
    throw new Error(parseErrorText(text));
  }

  return JSON.parse(text) as JobData;
}

export function toFileUrl(pathOrNull: string | null): string | null {
  if (!pathOrNull) {
    return null;
  }

  if (pathOrNull.startsWith("outputs/")) {
    return `/files/${pathOrNull.slice("outputs/".length)}`;
  }

  if (pathOrNull.startsWith("/files/")) {
    return pathOrNull;
  }

  return `/files/${pathOrNull}`;
}
