const form = document.getElementById("segment-form");
const fileInput = document.getElementById("file-input");
const taskSelect = document.getElementById("task-select");
const jobMeta = document.getElementById("job-meta");
const statusBox = document.getElementById("status-box");
const resultSection = document.getElementById("result-section");
const previewList = document.getElementById("preview-list");
const downloadList = document.getElementById("download-list");
const runtimeGpu = document.getElementById("runtime-gpu");

let pollHandle = null;

function toFilesUrl(relativePath) {
  if (!relativePath) return null;
  if (relativePath.startsWith("outputs/")) {
    return `/files/${relativePath.slice("outputs/".length)}`;
  }
  return `/files/${relativePath}`;
}

function clearResults() {
  resultSection.hidden = true;
  previewList.innerHTML = "";
  downloadList.innerHTML = "";
  runtimeGpu.textContent = "";
}

function stopPolling() {
  if (pollHandle) {
    clearInterval(pollHandle);
    pollHandle = null;
  }
}

function renderStatus(job) {
  const statusPayload = {
    job_id: job.job_id,
    status: job.status,
    created_at: job.created_at,
    started_at: job.started_at,
    completed_at: job.completed_at,
    error: job.error,
  };
  statusBox.textContent = JSON.stringify(statusPayload, null, 2);
}

function renderCompleted(job) {
  clearResults();
  resultSection.hidden = false;

  const gpu = job.gpu || {};
  runtimeGpu.textContent = JSON.stringify(
    {
      runtime_sec: job.runtime_sec,
      gpu_name: gpu.name,
      gpu_uuid: gpu.uuid,
      gpu_utilization_pct: gpu.utilization_pct,
      gpu_mem_used_mb: gpu.mem_used_mb,
      gpu_mem_total_mb: gpu.mem_total_mb,
      gpu_temperature_c: gpu.temperature_c,
    },
    null,
    2
  );

  const previews = (job.outputs && job.outputs.previews) || [];
  previews.forEach((previewPath) => {
    const url = toFilesUrl(previewPath);
    const img = document.createElement("img");
    img.src = url;
    img.alt = previewPath;
    previewList.appendChild(img);

    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = url;
    a.textContent = `Download ${previewPath.split("/").pop()}`;
    a.target = "_blank";
    li.appendChild(a);
    downloadList.appendChild(li);
  });

  const masks = (job.outputs && job.outputs.masks) || {};
  Object.entries(masks).forEach(([organ, path]) => {
    if (!path) return;
    const url = toFilesUrl(path);
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = url;
    a.textContent = `Download ${organ} mask`;
    a.target = "_blank";
    li.appendChild(a);
    downloadList.appendChild(li);
  });
}

async function pollJob(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      statusBox.textContent = `Polling failed: HTTP ${response.status}`;
      stopPolling();
      return;
    }

    const job = await response.json();
    renderStatus(job);

    if (job.status === "completed") {
      renderCompleted(job);
      stopPolling();
    } else if (job.status === "failed") {
      clearResults();
      stopPolling();
    }
  } catch (error) {
    statusBox.textContent = `Polling failed: ${error}`;
    stopPolling();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  stopPolling();
  clearResults();

  const file = fileInput.files[0];
  if (!file) {
    statusBox.textContent = "Please choose a file.";
    return;
  }

  const targets = Array.from(document.querySelectorAll('input[name="target"]:checked')).map(
    (item) => item.value
  );
  if (targets.length === 0) {
    statusBox.textContent = "Please select at least one target.";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("task", taskSelect.value);
  formData.append("targets", JSON.stringify(targets));

  statusBox.textContent = "Submitting job...";

  try {
    const response = await fetch("/segment", {
      method: "POST",
      body: formData,
    });

    const payload = await response.json();
    if (!response.ok) {
      statusBox.textContent = payload.detail || `Submission failed: HTTP ${response.status}`;
      return;
    }

    jobMeta.textContent = `Job ID: ${payload.job_id}`;
    statusBox.textContent = `Job ${payload.job_id} submitted. Waiting...`;

    await pollJob(payload.poll_url);
    pollHandle = setInterval(() => pollJob(payload.poll_url), 2000);
  } catch (error) {
    statusBox.textContent = `Submission failed: ${error}`;
  }
});
