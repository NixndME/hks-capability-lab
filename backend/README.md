# HKS Capability Portal — Backend

FastAPI service. Reads `../tests/definitions/*.yaml` as its source of truth
and, in local mode, does **read-only** Kubernetes discovery (never
create/patch/delete — see `app/k8s.py`).

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8080
```

## Endpoints (phase 1)

- `GET /health` — liveness
- `GET /ready` — readiness (test definitions loaded)
- `GET /api/info` — app metadata, mode (hosted/local), cluster connection status
- `GET /api/tests` — all test definitions, grouped by category, with pass/fail/etc. summary counts
- `GET /api/tests/{id}` — a single test definition

## Mode

- `PORTAL_MODE=hosted` — never touches a kubeconfig or cluster, ever.
- `PORTAL_MODE=local` (default) — attempts read-only cluster discovery if a
  kubeconfig is present (`KUBECONFIG` env var or `~/.kube/config`); degrades
  to `kubernetes.connected: false` on any failure rather than erroring.

## Not yet implemented (later phases)

Live test *execution* (create/apply/delete against a cluster) belongs in
`../tests/validation/` and is intentionally not part of this skeleton —
`app/k8s.py` is discovery-only by design.
