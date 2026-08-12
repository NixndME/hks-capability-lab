from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import definitions

router = APIRouter()


@router.get("/health")
def health():
    """Liveness: the process is up. Does not touch definitions or the cluster."""
    return {"status": "ok"}


@router.get("/ready")
def ready():
    """Readiness: the app can serve real requests -- test definitions loaded
    successfully. Kubernetes connectivity is NOT part of readiness: local
    mode without a cluster is a valid, ready state (browse-only)."""
    try:
        count = len(definitions.load_all())
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(status_code=503, content={"status": "not-ready", "error": str(exc)})
    return {"status": "ready", "test_definitions_loaded": count}
