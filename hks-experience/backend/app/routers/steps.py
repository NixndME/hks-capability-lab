from fastapi import APIRouter, Cookie, HTTPException, Response

from .. import executor, k8s, state, workflow

router = APIRouter()

SESSION_COOKIE = "hks_experience_session"


def _session(response: Response, session: str | None) -> str:
    if session:
        return session
    new_id = state.new_session_id()
    response.set_cookie(SESSION_COOKIE, new_id, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return new_id


def _status_map(stored: dict) -> dict[str, str]:
    """Single pass over steps in journey order, so a downstream step can see
    an upstream step's real (reconciled-from-cluster or session-stored)
    status when deciding LOCKED vs. AVAILABLE -- computing each step's
    status independently would miss prerequisites satisfied by cluster
    state that was never explicitly recorded in this session."""
    resolved: dict[str, str] = {}
    completed_or_skipped: set[str] = set()
    for step in workflow.load_steps():
        step_id = step["id"]
        if step_id in stored:
            status = stored[step_id]
        else:
            status = k8s.reconcile_step(step_id) or None
            if not status:
                if workflow.prerequisites_met(step_id, completed_or_skipped):
                    status = "AVAILABLE"
                else:
                    status = "LOCKED"
        resolved[step_id] = status
        if status in ("COMPLETED", "SKIPPED", "NOT_APPLICABLE"):
            completed_or_skipped.add(step_id)
    return resolved


@router.get("/api/steps")
def list_steps(response: Response, hks_experience_session: str | None = Cookie(default=None)):
    session_id = _session(response, hks_experience_session)
    stored = state.get_session(session_id)
    statuses = _status_map(stored)
    steps = []
    for step in workflow.load_steps():
        s = dict(step)
        s["status"] = statuses[step["id"]]
        steps.append(s)
    return {"steps": steps, "categories": workflow.categories()}


@router.get("/api/steps/{step_id}")
def get_step(step_id: str, response: Response, hks_experience_session: str | None = Cookie(default=None)):
    step = workflow.get_step(step_id)
    if not step:
        raise HTTPException(404, f"step '{step_id}' not found")
    session_id = _session(response, hks_experience_session)
    stored = state.get_session(session_id)
    statuses = _status_map(stored)
    result = dict(step)
    result["status"] = statuses[step_id]
    return result


def _guarded(step_id: str, session_id: str) -> dict:
    step = workflow.get_step(step_id)
    if not step:
        raise HTTPException(404, f"step '{step_id}' not found")
    stored = state.get_session(session_id)
    status = _status_map(stored)[step_id]
    if status == "LOCKED":
        raise HTTPException(409, "prerequisites not met yet")
    return step


def _run_cluster_prep(step_id: str, session_id: str) -> dict:
    """Cluster Preparation is special-cased to use the Kubernetes python
    client directly (k8s.py) rather than shim.sh/kubectl -- its only job is
    "can we connect and what optional capabilities exist", which must never
    be entangled with deploy-time machinery (StorageClass/IngressClass
    resolution etc) that the LATER mutating steps need. See k8s.py's
    discover_cluster/discover_capabilities and the "optional infrastructure
    absence is not an error" rule."""
    cluster = k8s.discover_cluster()
    if not cluster.connected:
        final_status = "BLOCKED"
        state.set_status(session_id, step_id, final_status)
        err = cluster.error
        return {
            "step_id": step_id,
            "executed": True,
            "result": "BLOCKED",
            "status": final_status,
            "log": [f"BLOCKED  {err.code}: {err.message}" if err else "BLOCKED  Kubernetes not reachable"],
            "error": err.to_dict() if err else None,
            "cluster_status": {"status": "blocked", **(err.to_dict() if err else {})},
        }

    caps = k8s.discover_capabilities()
    log_lines = [
        "PASS  Connected",
        f"INFO  context={cluster.context}",
        f"INFO  kubernetes={cluster.version}",
        f"INFO  nodes={cluster.node_count}",
        f"INFO  cni={caps.cni}",
        f"INFO  storage={caps.storage}",
        f"INFO  prometheus={caps.prometheus}",
        f"INFO  ingress={caps.ingress}",
        f"INFO  gateway_api={caps.gateway_api}",
        f"INFO  cluster_autoscaler={caps.cluster_autoscaler}",
    ]
    final_status = "COMPLETED"
    state.set_status(session_id, step_id, final_status)
    return {
        "step_id": step_id,
        "executed": True,
        "result": "PASS",
        "status": final_status,
        "log": log_lines,
        "error": None,
        "cluster_status": {
            "status": "ready",
            "cluster": {"context": cluster.context, "version": cluster.version, "nodes": cluster.node_count},
            "capabilities": {
                "cni": caps.cni, "storage": caps.storage, "prometheus": caps.prometheus,
                "ingress": caps.ingress, "gateway_api": caps.gateway_api, "cluster_autoscaler": caps.cluster_autoscaler,
            },
        },
    }


@router.post("/api/steps/{step_id}/run")
def run_step(step_id: str, response: Response, hks_experience_session: str | None = Cookie(default=None)):
    session_id = _session(response, hks_experience_session)
    step = _guarded(step_id, session_id)

    if step_id == "cluster-prep":
        return _run_cluster_prep(step_id, session_id)

    executor_key = (step.get("verify") or {}).get("executor")
    if not executor_key:
        raise HTTPException(400, "this step has no automated action -- copy the command and run it yourself")
    pre_attempt_status = state.get_session(session_id).get(step_id, "AVAILABLE")
    state.set_status(session_id, step_id, "IN_PROGRESS")
    result = executor.run_action(executor_key)

    if result.result == "NOT_EXECUTED":
        # Execution disabled (hosted mode) -- not an attempt at all, revert
        # to whatever the step's status was before this call.
        state.set_status(session_id, step_id, pre_attempt_status)
        final_status = pre_attempt_status
    elif result.result in ("BLOCKED", "ERROR"):
        # A missing prerequisite (cluster connectivity, RBAC) or an
        # infra-level crash inside this app -- neither is the same as the
        # capability test actually running and failing. BLOCKED does not
        # satisfy this step's prerequisites for downstream steps either.
        final_status = "BLOCKED"
        state.set_status(session_id, step_id, final_status)
    else:
        final_status = {"PASS": "COMPLETED", "FAIL": "FAILED", "SKIP": "SKIPPED"}[result.result]
        state.set_status(session_id, step_id, final_status)

    return {
        "step_id": step_id,
        "executed": result.executed,
        "result": result.result,
        "status": final_status,
        "log": result.log_lines,
        "error": (
            {"code": result.error_code, "message": result.error_message, "remediation": result.remediation}
            if result.error_code
            else None
        ),
    }


@router.post("/api/steps/{step_id}/skip")
def skip_step(step_id: str, response: Response, hks_experience_session: str | None = Cookie(default=None)):
    session_id = _session(response, hks_experience_session)
    step = workflow.get_step(step_id)
    if not step:
        raise HTTPException(404, f"step '{step_id}' not found")
    if not step.get("skippable", True):
        raise HTTPException(400, "this step cannot be skipped")
    state.set_status(session_id, step_id, "SKIPPED")
    return {"step_id": step_id, "status": "SKIPPED"}
