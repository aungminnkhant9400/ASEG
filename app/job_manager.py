import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.adapters.organ_adapter import OrganAdapter
from app.gpu_monitor import GPUMonitor

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_runtime_dirs() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


class JobManager:
    def __init__(self) -> None:
        ensure_runtime_dirs()
        self.gpu_monitor = GPUMonitor()

    def _to_relative(self, path: Path) -> str:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()

    def _job_output_dir(self, job_id: str) -> Path:
        return OUTPUTS_DIR / job_id

    def _job_json_path(self, job_id: str) -> Path:
        return self._job_output_dir(job_id) / "job.json"

    def write_job(self, job_dict: Dict[str, Any]) -> None:
        job_id = job_dict["job_id"]
        job_dir = self._job_output_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)

        job_json_path = self._job_json_path(job_id)
        with job_json_path.open("w", encoding="utf-8") as f:
            json.dump(job_dict, f, indent=2)

    def read_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        job_json_path = self._job_json_path(job_id)
        if not job_json_path.exists():
            return None

        with job_json_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def create_job(
        self,
        file_bytes: bytes,
        original_filename: str,
        task: str,
        targets: List[str],
    ) -> str:
        ensure_runtime_dirs()

        job_id = str(uuid4())
        upload_dir = UPLOADS_DIR / job_id
        output_dir = OUTPUTS_DIR / job_id
        masks_dir = output_dir / "masks"
        previews_dir = output_dir / "previews"

        upload_dir.mkdir(parents=True, exist_ok=True)
        masks_dir.mkdir(parents=True, exist_ok=True)
        previews_dir.mkdir(parents=True, exist_ok=True)

        lower_name = original_filename.lower()
        extension = ".nii.gz" if lower_name.endswith(".nii.gz") else ".nii"
        input_path = upload_dir / f"input{extension}"

        with input_path.open("wb") as f:
            f.write(file_bytes)

        logs_path = output_dir / "logs.txt"
        logs_path.touch(exist_ok=True)

        job_dict: Dict[str, Any] = {
            "job_id": job_id,
            "task": task,
            "targets": targets,
            "status": "pending",
            "created_at": utc_now_iso(),
            "started_at": None,
            "completed_at": None,
            "runtime_sec": None,
            "input_path": self._to_relative(input_path),
            "outputs": {
                "masks": {
                    "lungs": self._to_relative(masks_dir / "lungs.nii.gz") if "lungs" in targets else None,
                    "liver": self._to_relative(masks_dir / "liver.nii.gz") if "liver" in targets else None,
                },
                "previews": [],
            },
            "gpu": {
                "name": None,
                "uuid": None,
                "utilization_pct": None,
                "mem_used_mb": None,
                "mem_total_mb": None,
                "temperature_c": None,
            },
            "error": None,
        }

        self.write_job(job_dict)
        return job_id

    def run_job(self, job_id: str) -> None:
        job = self.read_job(job_id)
        if job is None:
            return

        output_dir = self._job_output_dir(job_id)
        logs_path = output_dir / "logs.txt"
        input_path = BASE_DIR / job["input_path"]

        job["status"] = "running"
        job["started_at"] = utc_now_iso()
        job["error"] = None
        self.write_job(job)

        started = perf_counter()

        try:
            adapter = OrganAdapter(
                job_id=job_id,
                targets=job["targets"],
                uploads_dir=UPLOADS_DIR,
                outputs_dir=OUTPUTS_DIR,
                logs_path=logs_path,
            )

            processed_path = adapter.preprocess(input_path)
            prediction_dir = adapter.infer(processed_path)
            mask_paths = adapter.postprocess(prediction_dir)
            preview_paths = adapter.generate_previews(input_path, mask_paths)

            runtime_sec = round(perf_counter() - started, 3)
            gpu_stats = self.gpu_monitor.get_stats()

            job["outputs"]["masks"]["lungs"] = (
                self._to_relative(mask_paths["lungs"]) if "lungs" in mask_paths else None
            )
            job["outputs"]["masks"]["liver"] = (
                self._to_relative(mask_paths["liver"]) if "liver" in mask_paths else None
            )
            job["outputs"]["previews"] = [self._to_relative(path) for path in preview_paths]
            job["gpu"] = gpu_stats
            job["status"] = "completed"
            job["completed_at"] = utc_now_iso()
            job["runtime_sec"] = runtime_sec
            job["error"] = None
            self.write_job(job)
        except Exception as exc:
            runtime_sec = round(perf_counter() - started, 3)
            logs_path.parent.mkdir(parents=True, exist_ok=True)
            with logs_path.open("a", encoding="utf-8") as log_file:
                log_file.write("\n\n=== Internal Error ===\n")
                log_file.write(f"{type(exc).__name__}: {exc}\n")
                log_file.write(traceback.format_exc())

            job["status"] = "failed"
            job["completed_at"] = utc_now_iso()
            job["runtime_sec"] = runtime_sec
            job["error"] = str(exc)
            self.write_job(job)


job_manager = JobManager()
