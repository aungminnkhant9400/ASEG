# ASEG

ASEG is a local Dockerized medical imaging segmentation platform.

Current scope:
- **v1**: CT organ segmentation (lungs + liver) using FastAPI + TotalSegmentator.

Roadmap:
- Add more organ targets/tasks.
- Evolve toward the long-term goal: **tumor segmentation**.

## What users can do (v1)

- Upload CT NIfTI (`.nii` or `.nii.gz`)
- Segment lungs and/or liver
- See job progress and live status
- View axial/sagittal/coronal preview overlays
- Download generated masks and previews

The backend and UI are designed to be extended for future tasks without replacing the whole app.

## First-run timing (important)

The first run is usually much slower because Docker and TotalSegmentator dependencies/models are being installed/downloaded.

- First image build: can take several minutes (or longer on slow network)
- First segmentation run: can take longer because model weights/cache are populated
- Later builds/runs: usually much faster due to Docker layer cache and model cache reuse

Runtime speed after initial setup depends on your hardware:
- GPU server (recommended): much faster
- CPU-only machine: significantly slower

## Prerequisites

- Docker installed
- For GPU mode: NVIDIA driver + Docker GPU support (`--gpus all`)

## Quick start (Docker)

Build image:

```bash
docker build -t aseg:latest .
```

Run (CPU mode):

```bash
docker run --rm -p 8000:8000 --name aseg aseg:latest
```

Run (GPU mode):

```bash
docker run --rm --gpus all -p 8000:8000 --name aseg aseg:latest
```

Open UI:

- `http://localhost:8000`

## Recommended run with persistent data/cache

To avoid re-downloading model/cache each time, mount host folders:

```powershell
docker run --rm -p 8000:8000 `
  -v "${PWD}\data\uploads:/app/uploads" `
  -v "${PWD}\data\outputs:/app/outputs" `
  -v "${PWD}\data\ts_cache:/root/.totalsegmentator" `
  -v "${PWD}\data\hf_cache:/root/.cache" `
  --name aseg `
  aseg:latest
```

GPU + persistent data:

```powershell
docker run --rm --gpus all -p 8000:8000 `
  -v "${PWD}\data\uploads:/app/uploads" `
  -v "${PWD}\data\outputs:/app/outputs" `
  -v "${PWD}\data\ts_cache:/root/.totalsegmentator" `
  -v "${PWD}\data\hf_cache:/root/.cache" `
  --name aseg `
  aseg:latest
```

## Optional env settings

- `ASEG_AUTO_DELETE_UPLOADS=true`
  - Deletes `/app/uploads/<job_id>/` automatically **after successful completion**.
  - Default is `false`.
  - Failed jobs keep uploads for debugging.

Example:

```powershell
docker run --rm -p 8000:8000 `
  -e ASEG_AUTO_DELETE_UPLOADS=true `
  --name aseg `
  aseg:latest
```

## API contract

- `POST /segment` (multipart/form-data)
  - `file`: `.nii` or `.nii.gz`
  - `task`: `organ`
  - `targets`: JSON string list, example `["lungs","liver"]`
- `GET /jobs/{job_id}` returns job JSON

PowerShell curl example:

```powershell
curl.exe -X POST "http://localhost:8000/segment" --form "file=@C:/path/to/ct_scan.nii.gz" --form "task=organ" --form-string "targets=[\"lungs\",\"liver\"]"
```

## Output layout

Inside container:

- `uploads/{job_id}/input.nii(.gz)`
- `outputs/{job_id}/job.json`
- `outputs/{job_id}/logs.txt`
- `outputs/{job_id}/masks/lungs.nii.gz`
- `outputs/{job_id}/masks/liver.nii.gz`
- `outputs/{job_id}/previews/overlay_0.png`, `overlay_1.png`, `overlay_2.png`

Downloads are served at `/files`:

- `/files/<job_id>/masks/lungs.nii.gz`
- `/files/<job_id>/masks/liver.nii.gz`
- `/files/<job_id>/previews/overlay_0.png`

## UI routes

- `/` home/upload page
- `/jobs/:jobId` results page
- `/about` short project info

## Local development (optional)

Backend:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open Vite dev UI:

- `http://localhost:5173`

## Troubleshooting

- Build seems stuck on `npm install`:
  - first build may take a long time; wait
  - if still stuck, rebuild with `--progress=plain` and check network/registry
- GPU run fails with WSL/no adapter:
  - run CPU mode or run on a host where `docker run --gpus all ... nvidia-smi` works
- `/jobs/<id>` not updating:
  - verify container logs and ensure the job status becomes `running/completed/failed`
