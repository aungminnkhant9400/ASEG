export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface JobData {
  job_id: string;
  task: string;
  targets: string[];
  status: JobStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  runtime_sec: number | null;
  input_path: string;
  outputs: {
    masks: {
      lungs: string | null;
      liver: string | null;
    };
    previews: string[];
  };
  gpu: {
    name: string | null;
    uuid: string | null;
    utilization_pct: number | null;
    mem_used_mb: number | null;
    mem_total_mb: number | null;
    temperature_c: number | null;
  };
  error: string | null;
}

export interface SegmentSubmitResponse {
  job_id: string;
  status: "pending";
  poll_url: string;
}
