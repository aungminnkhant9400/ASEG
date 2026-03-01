from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.job_manager import ensure_runtime_dirs

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST_DIR = BASE_DIR / "frontend_dist"
FRONTEND_INDEX_PATH = FRONTEND_DIST_DIR / "index.html"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"


def _frontend_index_response() -> HTMLResponse:
    if FRONTEND_INDEX_PATH.exists():
        return HTMLResponse(content=FRONTEND_INDEX_PATH.read_text(encoding="utf-8"))

    return HTMLResponse(
        content=(
            "<html><body><h2>Frontend bundle not found.</h2>"
            "<p>Build the React app to serve the ASEG UI.</p></body></html>"
        ),
        status_code=503,
    )


def create_app() -> FastAPI:
    app = FastAPI(title="ASEG")

    ensure_runtime_dirs()

    app.mount("/files", StaticFiles(directory=str(BASE_DIR / "outputs")), name="files")

    if FRONTEND_ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS_DIR)), name="assets")

    app.include_router(api_router)

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return _frontend_index_response()

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        blocked_prefixes = ("files/", "assets/", "segment", "docs/", "redoc/")
        blocked_exact = {"files", "assets", "openapi.json", "docs", "redoc"}

        if full_path in blocked_exact or any(full_path.startswith(prefix) for prefix in blocked_prefixes):
            raise HTTPException(status_code=404, detail="Not found")

        candidate = (FRONTEND_DIST_DIR / full_path).resolve()
        frontend_root = FRONTEND_DIST_DIR.resolve()

        if frontend_root in candidate.parents and candidate.is_file():
            return FileResponse(path=str(candidate))

        return _frontend_index_response()

    return app


app = create_app()
