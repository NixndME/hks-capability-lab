from fastapi import APIRouter

from .. import workflow

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    try:
        count = len(workflow.load_steps())
    except Exception as exc:  # noqa: BLE001
        return {"status": "not-ready", "error": str(exc)}
    return {"status": "ready", "steps_loaded": count}
