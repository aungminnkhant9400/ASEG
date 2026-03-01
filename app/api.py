import json
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.job_manager import job_manager

router = APIRouter()
ALLOWED_TARGETS = {"lungs", "liver"}
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_INDEX_PATH = BASE_DIR / "frontend_dist" / "index.html"


def _wants_html(request: Request) -> bool:
    accept = (request.headers.get("accept") or "").lower()
    return "text/html" in accept and "application/json" not in accept


def _unwrap_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def _best_effort_parse_targets(raw_targets: str) -> List[str]:
    value = (raw_targets or "").strip()
    if not value:
        return []

    candidates = []
    for candidate in (
        value,
        _unwrap_quotes(value),
        value.replace('\\"', '"').replace("\\'", "'"),
        _unwrap_quotes(value.replace('\\"', '"').replace("\\'", "'")),
    ):
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                return parsed
        except json.JSONDecodeError:
            continue

    # Fallback: allow values like lungs,liver or [lungs liver]
    text = _unwrap_quotes(value.replace('\\"', '"').replace("\\'", "'"))
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    text = text.replace('"', "").replace("'", "")
    if not text:
        return []

    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return [part.strip() for part in text.split() if part.strip()]


def _parse_targets(raw_targets: str) -> List[str]:
    parsed = _best_effort_parse_targets(raw_targets)
    if not parsed:
        raise HTTPException(
            status_code=400,
            detail='targets must be a JSON string list, e.g. ["lungs","liver"]',
        )

    normalized = [item.strip().lower() for item in parsed if item.strip()]
    if not normalized:
        raise HTTPException(status_code=400, detail="targets must be non-empty")

    invalid = sorted(set(normalized) - ALLOWED_TARGETS)
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unsupported targets: {', '.join(invalid)}")

    deduped: List[str] = []
    for target in normalized:
        if target not in deduped:
            deduped.append(target)

    return deduped


@router.post("/segment")
async def submit_segmentation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    task: str = Form("organ"),
    targets: str = Form("[\"lungs\",\"liver\"]"),
) -> dict:
    filename = file.filename or ""
    lower_name = filename.lower()

    if not (lower_name.endswith(".nii") or lower_name.endswith(".nii.gz")):
        raise HTTPException(status_code=400, detail="file must end with .nii or .nii.gz")

    if task != "organ":
        raise HTTPException(status_code=400, detail='v1 supports only task="organ"')

    parsed_targets = _parse_targets(targets)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="uploaded file is empty")

    job_id = job_manager.create_job(
        file_bytes=file_bytes,
        original_filename=filename,
        task=task,
        targets=parsed_targets,
    )

    background_tasks.add_task(job_manager.run_job, job_id)

    return {"job_id": job_id, "status": "pending", "poll_url": f"/jobs/{job_id}"}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request):
    # Allow browser navigation to /jobs/:jobId (React route) while keeping API JSON for fetch/curl clients.
    if _wants_html(request) and FRONTEND_INDEX_PATH.exists():
        return HTMLResponse(content=FRONTEND_INDEX_PATH.read_text(encoding="utf-8"))

    job = job_manager.read_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    if job.get("status") == "running":
        job["gpu"] = job_manager.gpu_monitor.get_stats()

    return job
