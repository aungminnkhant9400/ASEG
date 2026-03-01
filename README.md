# ASEG

ASEG is a local Dockerized web app for CT organ segmentation (lungs + liver) using FastAPI + TotalSegmentator.

## UI

- Home: `/` for upload and run
- Results: `/jobs/:jobId` with status, runtime, GPU metrics, previews, downloads, and share-link copy
- About: `/about`

## API (unchanged)

- `POST /segment` multipart form:
  - `file` (`.nii` or `.nii.gz`)
  - `task` (`organ`)
  - `targets` JSON string (example: `["lungs","liver"]`)
- `GET /jobs/{job_id}` returns job JSON for API clients.

## Local dev (optional)

Backend:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend (separate terminal):

```bash
cd frontend
npm install
npm run dev
```

Open Vite app at `http://localhost:5173`.

## Docker build and run

Build:

```bash
docker build -t aseg:latest .
```

Run:

```bash
docker run --rm -p 8000:8000 aseg:latest
```

GPU run (lab server):

```bash
docker run --rm --gpus all -p 8000:8000 aseg:latest
```

Open UI: `http://localhost:8000`

## Submit a job from CLI

PowerShell/curl example:

```powershell
curl.exe -X POST "http://localhost:8000/segment" --form "file=@C:/path/to/ct_scan.nii.gz" --form "task=organ" --form-string "targets=[\"lungs\",\"liver\"]"
```

## Output locations

- `uploads/{job_id}/input.nii(.gz)`
- `outputs/{job_id}/job.json`
- `outputs/{job_id}/logs.txt`
- `outputs/{job_id}/masks/lungs.nii.gz`
- `outputs/{job_id}/masks/liver.nii.gz`
- `outputs/{job_id}/previews/overlay_0.png` ...

Downloads are exposed from `/files`:

- `/files/<job_id>/masks/lungs.nii.gz`
- `/files/<job_id>/masks/liver.nii.gz`
- `/files/<job_id>/previews/overlay_0.png`
