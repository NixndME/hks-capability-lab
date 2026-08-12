# Initial Architecture Assessment

Date: 2026-08-12
Scope: pre-work inventory before building the HKS Capability Portal on top of
the existing validated HKS capability test suite. Nothing described in
"Current state" was modified to produce this document.

## Current state (what already exists and is validated)

The repository is a **bash + kubectl + envsubst** test harness, not yet a web
product. Concretely:

- `run-hks-test.sh` — interactive menu / `--all` / `--cleanup` CLI, the single
  entrypoint. Sources `scripts/lib.sh` for discovery + logging helpers.
- `scripts/lib.sh` — cluster auto-discovery (StorageClass, IngressClass,
  Gateway API, Prometheus Operator, metrics API, Cluster Autoscaler,
  LoadBalancer infra) and `envsubst`-based render/apply/delete helpers. Only
  six variables are ever substituted into YAML (`$NAMESPACE $STORAGE_CLASS
  $TEST_HOST $APP_IMAGE $APP_REPLICAS $INGRESS_CLASS` plus the Prometheus
  SA/namespace pair) — nothing else is templated.
- `scripts/validate-*.sh` (networking, storage, prometheus, autoscaler,
  rollout, resiliency) — one script per capability domain, called from
  `run-hks-test.sh`.
- `hks-capability-lab.yaml` — the core app manifest: Namespace, ConfigMap
  (embeds the entire `app/app.py` source — no image build), Secret,
  ServiceAccount/Role/RoleBinding, Deployment (with pod anti-affinity,
  topology spread, readiness/liveness probes, resource requests/limits),
  two Services (ClusterIP + NodePort), HPA, PDB, Ingress, plus the additive
  Prometheus scrape-access RoleBinding and a ServiceMonitor. This is the one
  piece of YAML every deployment mode should keep working.
- `manifests/*.yaml` — blue-green, canary, network-policy, storage-test,
  monitoring: demonstration resources applied/deleted on demand, not part of
  the core app.
- `app/app.py` — stdlib-only Python HTTP app (no dependencies, runs on stock
  `python:3.12-alpine`). Serves an inline dark-themed HTML dashboard,
  `/healthz` `/readyz` `/livez`, `/api/info`, `/api/load`, `/api/chaos/*`,
  and a hand-rolled `/metrics` Prometheus exposition endpoint. Version/color
  driven entirely by env vars (`APP_VERSION`, `APP_COLOR`) — this is how
  rolling update / rollback / blue-green / canary all work without an image
  rebuild.
- `evidence/` — real command output from an actual run against a live HKS
  cluster (`kubernetes-admin@HKS`, still the active kubeconfig context in
  this environment) on 2026-08-12, plus a reference discovery snapshot.
- Nine top-level markdown docs (`README.md`, `TEST_RESULTS.md`,
  `HKS_CAPABILITY_MATRIX.md`, `HKS_PRODUCT_VALIDATION_REPORT.md`,
  `NETWORKING_DECISION.md`, `STORAGE_VALIDATION.md`,
  `PROMETHEUS_VALIDATION.md`, `AUTOSCALER_VALIDATION.md`,
  `SCHEDULING_VALIDATION.md`) documenting what was tested and why, with two
  real platform bugs found and fixed (ServiceMonitor RBAC gap, duplicate
  scrape via a dedicated `hks-capability-lab/metrics: primary` label).

Result claimed and evidenced: 26/28 capabilities PASS; Cluster Autoscaler
NOT AVAILABLE (no node-pool infra on this static KVM cluster) and Gateway
API NOT VALIDATED (would require a cluster-scoped change) — both correctly
reported as gaps, not silently skipped.

**None of this is currently containerized, none of it has a web frontend or
backend API, and there is no Helm chart anywhere in the repo.** The "portal"
requested is a new product to be built *on top of* this harness — the test
logic, discovery logic, and manifests are the reusable core; the CLI is the
existing "engine" a backend API needs to wrap, not replace.

## Toolchain available in this environment

| Tool | Status |
|---|---|
| `podman` | 6.0.2, present (also aliased as `docker`) |
| `helm` | v4.2.2, present |
| `kubectl` | present, **active context is `kubernetes-admin@HKS` — a real cluster**, same one the existing evidence was captured against |
| `python3` | 3.14.6, present; `fastapi` and `kubernetes` PyPI packages **not installed** |
| `node`/`npm` | **not installed** — a React/TypeScript/Vite frontend cannot be built or dev-served on this host directly; it would have to be built inside a multi-stage `Containerfile` (podman can do this without a host Node install) or Node would need to be installed first |

Implication: local browser QA of a React frontend (spec section 78) requires
either installing Node on this host or doing every frontend iteration via
container rebuilds, which is slow for iterative UI work. Recommend
installing Node locally for development speed; container build remains the
source of truth for the shipped artifact either way.

## Scale of the requested work

The request (90 numbered sections) asks for, concretely:

1. A new React + TypeScript + Tailwind frontend implementing an 11-page IA,
   a 21-step guided wizard, a full shared component library, and a bespoke
   "Corporate Trust" design system (tokens given directly in the prompt —
   no separate uploaded file is present in this conversation, so the
   token/typography spec in the prompt itself is being treated as
   authoritative).
2. A new FastAPI backend wrapping the Kubernetes Python client for
   discovery/validation, serving the frontend, and exposing a REST API,
   with hosted vs. local mode detection and strict credential-handling
   rules (no kubeconfig upload, no browser-side cluster access).
3. A machine-readable test-definition system (YAML) that becomes the single
   source of truth driving UI, CLI, docs, and reports.
4. A first-class Helm chart (`helm/hks-capability-lab/`) covering ~15
   resource kinds, conditionally rendered, fully parameterized, plus 8
   example values files.
5. A production multi-stage `Containerfile`, `compose.yaml`, build/push/
   release scripts, and multi-arch (amd64/arm64) image support via Podman
   manifests — published to `docker.io/nixndme/hks-capability-lab` only
   when explicitly requested.
6. A parallel sample-application UI overhaul (still no fake data allowed —
   real pod/node/namespace/replica/traffic data only).
7. A reports engine (HTML/Markdown/JSON/ZIP) driven by the same test
   definitions.
8. A separate portal Kubernetes deployment path (`deploy/portal/`), distinct
   from the `manifests/` being validated.

This is a genuinely large, multi-domain build (frontend app, backend
service, packaging, release engineering, and a live-cluster-aware test
runner) — realistically several days of focused work even before Helm/
multi-arch/registry work, not something to land safely in one uninterrupted
pass without checkpoints. Two things also need an explicit decision before
code gets written, rather than being assumed silently:

- **Live cluster contact.** The active kubeconfig points at the same real
  HKS cluster the existing evidence was captured against. A backend that
  does live discovery/validation will talk to that cluster the moment it's
  run locally. That's consistent with "LOCAL MODE, Kubernetes Connected" as
  specified, but is worth confirming before any automated (as opposed to
  read-only discovery) test execution happens against it.
- **Registry publishing.** Per the request's own section 62/87 rules, images
  are only pushed to `docker.io/nixndme/hks-capability-lab` on explicit
  instruction — this assessment does not change that; no push will happen
  without a direct ask at that time.

## Recommended phasing

1. **Foundation** — repo restructure (`frontend/`, `backend/`, `sample-app/`,
   `tests/definitions/`, `deploy/portal/`), test-definition schema + YAML
   for the ~28 already-validated capabilities, `Containerfile`/`compose.yaml`
   skeleton, health endpoints. Preserves 100% of existing validated
   behavior; `run-hks-test.sh` keeps working unchanged.
2. **Backend** — FastAPI service: hosted/local mode detection, Kubernetes
   Python client discovery, wraps existing `scripts/validate-*.sh` /
   `run-hks-test.sh` logic rather than reimplementing it, REST API driven by
   the test definitions from phase 1.
3. **Frontend** — design tokens + component library, IA/navigation, landing
   page, guided wizard, YAML/Helm viewers, capability matrix, reports UI.
4. **Helm** — chart + examples + lint/template/package validation, Helm-mode
   parity with YAML mode for the capabilities that support it.
5. **Sample app UI** — redesign within the same design system, still backed
   by real runtime data only.
6. **Packaging/release** — multi-arch Podman build scripts, `deploy/portal/`,
   README overhaul; registry push and any live-cluster automated test run
   only on explicit request.

This assessment stops at phase 0 (discovery only, nothing changed). Next
step is agreeing the phase-1 file layout before writing code, since it
determines paths every later phase depends on.
