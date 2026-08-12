from fastapi import APIRouter, Cookie, Response

from .. import state, workflow
from .steps import _session, _status_map

router = APIRouter()


@router.get("/api/summary")
def summary(response: Response, hks_experience_session: str | None = Cookie(default=None)):
    session_id = _session(response, hks_experience_session)
    stored = state.get_session(session_id)
    statuses = _status_map(stored)
    steps = workflow.load_steps()
    counts = {
        "COMPLETED": 0, "SKIPPED": 0, "FAILED": 0, "NOT_APPLICABLE": 0,
        "AVAILABLE": 0, "IN_PROGRESS": 0,
    }
    by_category: dict[str, list[dict]] = {}
    for step in steps:
        status = statuses[step["id"]]
        counts[status] = counts.get(status, 0) + 1
        by_category.setdefault(step["category"], []).append(
            {"id": step["id"], "title": step["title"], "status": status}
        )
    total = len(steps)
    return {
        "total": total,
        "counts": counts,
        "categories": by_category,
        "complete": counts["COMPLETED"] + counts["SKIPPED"] + counts["NOT_APPLICABLE"] + counts["FAILED"] == total,
    }
