"""Per-session progress tracking. Deliberately simple (in-process dict,
keyed by a random cookie) -- this is a guided-journey lab tool, not a
multi-tenant SaaS backend. The frontend also caches progress in
localStorage for instant resume even before this reconciles; see
frontend/src/lib/progress.ts. Real, verifiable state (does the namespace
exist, is the deployment ready) always wins over a stale client-side
guess -- see routers/progress.py's reconcile endpoint.
"""
import secrets
import threading
from typing import Literal

Status = Literal[
    "AVAILABLE", "IN_PROGRESS", "COMPLETED", "SKIPPED", "FAILED", "NOT_APPLICABLE", "BLOCKED"
]

_LOCK = threading.Lock()
_SESSIONS: dict[str, dict[str, Status]] = {}


def new_session_id() -> str:
    return secrets.token_urlsafe(24)


def get_session(session_id: str) -> dict[str, Status]:
    with _LOCK:
        return dict(_SESSIONS.get(session_id, {}))


def set_status(session_id: str, step_id: str, status: Status) -> None:
    with _LOCK:
        _SESSIONS.setdefault(session_id, {})[step_id] = status
