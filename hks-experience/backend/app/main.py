from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .routers import artifacts, cluster, health, info, live, steps, summary

app = FastAPI(
    title=config.APP_DISPLAY_NAME,
    version=config.APP_VERSION,
    description="HKS guided customer experience — sits beside the existing validator, does not replace it.",
)

app.include_router(health.router)
app.include_router(info.router)
app.include_router(cluster.router)
app.include_router(steps.router)
app.include_router(summary.router)
app.include_router(artifacts.router)
app.include_router(live.router)

_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        return FileResponse(_FRONTEND_DIST / "index.html")
