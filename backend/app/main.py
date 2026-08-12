from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .routers import health, info, matrix, reports, tests

app = FastAPI(
    title=config.APP_DISPLAY_NAME,
    version=config.APP_VERSION,
    description="HKS Kubernetes Capability Validation Portal backend.",
)

app.include_router(health.router)
app.include_router(info.router)
app.include_router(tests.router)
app.include_router(matrix.router)
app.include_router(reports.router)

# Serve the built frontend (frontend/dist, produced by `npm run build`) when
# present -- single production container, no separate frontend deployment.
# In dev, `npm run dev`'s Vite proxy talks to this backend instead (see
# frontend/vite.config.ts), so this block is a no-op until a build exists.
_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        """Client-side routing (React Router) fallback: any path not matched
        by an API route above or a static asset gets index.html, which then
        resolves the route in the browser."""
        return FileResponse(_FRONTEND_DIST / "index.html")
