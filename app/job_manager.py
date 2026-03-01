import json
import logging
import os
import shutil
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
LOGGER = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_runtime_dirs() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


class JobManager:
    def __init__(self) -> None:
        ensure_runtime_dirs()
        self.gpu_monitor = GPUMonitor()
        self.auto_delete_uploads = self._env_bool("ASEG_AUTO_DELETE_UPLOADS", default=False)

    @staticmethod
    def _env_bool(name: str, default: bool = False) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    def _to_relative(self, path: Path) -> str:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()

    def _job_output_dir(self, job_id: str) -> Path:
        return OUTPUTS_DIR / job_id

    def _job_json_path(self, job_id: str) -> Path:
        return self._job_output_dir(job_id) / "job.json"

    def _append_job_log(self, logs_path: Path, message: str) -> None:
        logs_path.parent.mkdir(parents=True, exist_ok=True)
        with logs_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{message}\n")

    def _cleanup_job_uploads(self, job_id: str, logs_path: Path) -> None:
        upload_root = UPLOADS_DIR.resolve()
        job_upload_dir = (UPLOADS_DIR / job_id).resolve()

        if not self.auto_delete_uploads:
            warning_msg = (
                f"[cleanup] Skipped upload deletion for job {job_id}: "
                "ASEG_AUTO_DELETE_UPLOADS is disabled."
            )
            LOGGER.warning(warning_msg)
            self._append_job_log(logs_path, warning_msg)
            return

        if upload_root not in job_upload_dir.parents:
            warning_msg = (
                f"[cleanup] Refused upload deletion for job {job_id}: "
                f"path '{job_upload_dir}' is outside uploads root '{upload_root}'."
            )
            LOGGER.warning(warning_msg)
            self._append_job_log(logs_path, warning_msg)
            return

        if job_upload_dir == upload_root:
            warning_msg = (
                f"[cleanup] Refused upload deletion for job {job_id}: "
                "target path is uploads root."
            )
            LOGGER.warning(warning_msg)
            self._append_job_log(logs_path, warning_msg)
            return

        if not job_upload_dir.exists():
            warning_msg = (
                f"[cleanup] Skipped upload deletion for job {job_id}: "
                f"path '{job_upload_dir}' does not exist."
            )
            LOGGER.warning(warning_msg)
            self._append_job_log(logs_path, warning_msg)
            return

        shutil.rmtree(job_upload_dir, ignore_errors=True)
        if job_upload_dir.exists():
            warning_msg = (
                f"[cleanup] Upload deletion may be incomplete for job {job_id}: "
                f"path '{job_upload_dir}' still exists."
            )
            LOGGER.warning(warning_msg)
            self._append_job_log(logs_path, warning_msg)
            return

        info_msg = f"[cleanup] Deleted upload directory for job {job_id}: {job_upload_dir}"
        LOGGER.info(info_msg)
        self._append_job_log(logs_path, info_msg)

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
            self._cleanup_job_uploads(job_id=job_id, logs_path=logs_path)
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
