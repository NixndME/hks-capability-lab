# HKS Capability Lab

**HKS Kubernetes Capability Validation Portal** — validates what an HPE
Morpheus HKS Kubernetes cluster actually supports (networking, storage,
scaling, observability, deployment lifecycle, security, resiliency),
against a realistic sample workload, with evidence-backed results. Started
as a CLI test suite (`run-hks-test.sh`, still fully supported) and now also
ships as a web portal + Helm chart, all reading from the same
[test definitions](tests/definitions/) so the CLI, API, and generated
reports never drift from each other.

## Two things live in this repo

1. **The HKS Capability Portal** (`frontend/` + `backend/`) — the web UI a
   platform engineer uses to browse capabilities, view YAML/Helm, and
   generate reports.
2. **The HKS Sample Application** (`sample-app/app.py`) — the realistic
   workload deployed into a cluster to demonstrate/exercise those
   capabilities. The portal validates the platform; the sample app is the
   visible thing running on it.

## Hosted vs. Local mode

| | Hosted (`https://hks.nixndme.com`) | Local (Podman) |
|---|---|---|
| Cluster access | **Never** — no kubeconfig upload, ever | Optional, read-only discovery if `~/.kube/config` is mounted |
| What you get | Copyable YAML/Helm/kubectl commands, docs, manual verification workflow | Same, plus live cluster connection status (context, Kubernetes version, node count) |
| Credentials | Backend never touches Kubernetes credentials; browser never talks to Kubernetes directly | Same — the browser only ever talks to this backend (`backend/app/k8s.py`), never the Kubernetes API |

Hosted mode cannot and does not reach into your cluster — it gives you the
exact commands/manifests to run yourself and tells you what to expect.

## Local usage (Podman)

```bash
podman run --rm -p 8080:8080 docker.io/nixndme/hks-capability-lab:latest
# open http://localhost:8080 -- LOCAL MODE, Kubernetes Not Connected
```

Kubernetes-connected (read-only discovery only — kubeconfig mounted `:ro`,
never written to, never uploaded anywhere):

```bash
podman run --rm -p 8080:8080 \
  -v ~/.kube:/home/hkslab/.kube:ro \
  docker.io/nixndme/hks-capability-lab:latest
# LOCAL MODE, Kubernetes Connected
```

(Runtime user is non-root `hkslab`, home `/home/hkslab` — not `/root`.)

## Raw YAML usage (CLI)

```bash
cd hks-capability-lab
cp config.env.example config.env     # edit TEST_HOST etc. if you have real DNS
chmod +x run-hks-test.sh scripts/*.sh
./run-hks-test.sh          # interactive wizard
./run-hks-test.sh --all    # everything, non-interactively
./run-hks-test.sh --cleanup
```

Nothing in `hks-capability-lab.yaml` or `manifests/*.yaml` hard-codes an IP,
node name, or StorageClass — `run-hks-test.sh` discovers the StorageClass,
IngressClass, Gateway API/Prometheus Operator/metrics-API/Cluster
Autoscaler presence, and the Prometheus ServiceAccount's namespace/name (for
an additive RBAC grant — see `PROMETHEUS_VALIDATION.md`) at run time.
Switch clusters and re-run:

```bash
kubectl config use-context <another-hks-cluster>
./run-hks-test.sh --all
```

## Helm usage

The same workload, packaged as a Helm chart — raw YAML and Helm are both
fully supported, neither replaces the other:

```bash
helm lint helm/hks-capability-lab
helm install hks-lab helm/hks-capability-lab -f helm/examples/values-ingress.yaml
```

See `helm/hks-capability-lab/README.md` for chart details and
`helm/examples/` for eight ready-made scenarios (NodePort, LoadBalancer,
Ingress, Gateway API, storage, Prometheus, and a full/everything-on
variant).

## What this project tests

- **Networking:** ClusterIP, NodePort, LoadBalancer (API vs. infrastructure),
  Ingress/Gateway API, TLS, NetworkPolicy, DNS-based service discovery.
- **Workload management:** Deployments, rolling updates, rollback,
  scheduling constraints (affinity, anti-affinity, topology spread, taints/
  tolerations, resource requests).
- **Autoscaling:** Horizontal Pod Autoscaler and Cluster Autoscaler
  (distinguishing "not supported" from "supported but infrastructure
  unavailable").
- **Storage:** dynamic provisioning, persistence across pod restarts, and
  (read-only) integration with an existing Rook/Ceph install.
- **Observability:** integration with an existing Prometheus Operator stack
  via ServiceMonitor, without touching the existing Prometheus deployment.
- **Advanced deployment patterns:** blue/green and canary releases using
  only what the cluster already has (no service mesh installed for this).
- **Resiliency:** readiness/liveness probe behavior, pod rescheduling,
  service availability during disruption.

This suite deliberately **does not** just deploy an app and declare victory
— every capability above is exercised live against the cluster, observed,
and documented with real command output. See `TEST_RESULTS.md`,
`tests/definitions/`, and `evidence/` for the receipts. Result semantics are
never collapsed to pass/fail — see `tests/definitions/README.md` for the
distinction between `NOT_AVAILABLE` (infra gap), `NOT_VALIDATED` (in scope,
not yet exercised), and `FAIL`.

## What this project does NOT do

- It never deletes existing namespaces, workloads, PVCs, StorageClasses, or
  modifies the existing Prometheus/Rook-Ceph/Ingress installations.
- It does not install a second ingress/gateway controller — it discovers and
  reuses whatever already exists (see `NETWORKING_DECISION.md`).
- It never fabricates a PASS. Where a capability's infrastructure prerequisite
  is missing (e.g. no Cluster Autoscaler node-pool integration on a given
  cluster), that's reported explicitly as `NOT AVAILABLE`, distinct from a
  test failure — see `AUTOSCALER_VALIDATION.md` for a worked example.
- The portal backend never shells out `kubectl`/`helm` against a live
  cluster on your behalf for test *execution* — `backend/app/k8s.py` is
  read-only discovery only. Test execution stays in `run-hks-test.sh` /
  `scripts/validate-*.sh` today.

## Multi-architecture support

```bash
./scripts/build-multiarch.sh          # attempts linux/amd64 + linux/arm64
```

Builds the host architecture for real every time. The foreign architecture
is only built if this host has a *working* `binfmt_misc` QEMU registration
— rootless Podman without real host root often can't register one
persistently (a `podman run --privileged tonistiigi/binfmt` may report
success while only registering into its own container's mount namespace).
When that happens the script says so explicitly (`NOT EXECUTED: linux/arm64
... no functional binfmt_misc QEMU registration`) rather than silently
producing a single-arch image or claiming a build that didn't happen. It
also never claims runtime testing on an architecture it only cross-built —
see the script's own output for exactly what was/wasn't verified on a given
run.

## Build with Podman

```bash
./scripts/build-image.sh [tag]        # single-arch (host), builds + smoke-tests
./scripts/build-multiarch.sh [tag]    # amd64 + arm64 (see above), manifest list
./scripts/release.sh --dry-run        # fast, non-mutating checks only
./scripts/release.sh                  # full pipeline: YAML/Helm/frontend/backend checks, build, smoke test -- no push
./scripts/release.sh --push           # full pipeline, then prompts to push
```

`podman`, not Docker Desktop, is this project's build/run/inspect tool
throughout.

## Publish to registry

```bash
podman login docker.io
./scripts/push-image.sh <tag> [--manifest]
```

Never invoked automatically by any other script — publishing is always a
separate, explicit, interactively-confirmed step. Default repository is
`docker.io/nixndme/hks-capability-lab` (override with `IMAGE_REPOSITORY`).
Semver-looking tags (`1.0.0`) get a reuse warning; `latest`/`dev`/branch
tags are expected to move.

## Deploy the portal to HKS

```bash
cp deploy/portal/portal.env.example deploy/portal/portal.env   # edit PORTAL_DOMAIN, PORTAL_IMAGE
set -a && source deploy/portal/portal.env && set +a
envsubst < deploy/portal/portal.yaml | kubectl apply -f -
```

Separate from `manifests/`/`hks-capability-lab.yaml`, which deploy the
*sample workload the portal validates* — see `deploy/portal/README.md`.
Always runs `PORTAL_MODE=hosted`: this Deployment never mounts a
kubeconfig.

## Configure domain

Nothing hard-codes `hks.nixndme.com` into application logic — it's a
default only, overridden via env vars: `PUBLIC_BASE_URL`, `PORTAL_DOMAIN`,
`API_BASE_URL` (backend, see `backend/app/config.py`), local default is
`http://localhost:8080`. For testing against your own domain, the portal
tells you the exact DNS record (A/CNAME) your discovered ingress/gateway
setup needs — it never modifies external DNS itself.

## Security considerations

- Hosted mode never requests, accepts, or stores a kubeconfig.
- Local mode's kubeconfig mount is read-only by default
  (`-v ~/.kube:...:ro`); the backend only issues `get`/`list` calls (see
  `backend/app/k8s.py` for the strict read-only rule) and degrades to
  "not connected" on any failure rather than crashing.
  Test *execution* (create/apply/delete) is a separate, explicit concern
  handled by `run-hks-test.sh`, not the backend API.
- The browser never talks to Kubernetes directly — only to this project's
  own backend, over its own REST API.
- No Kubernetes credentials are ever exposed to frontend JavaScript or
  written to browser storage.
- Runtime container user is non-root (`hkslab`, uid 10001).
- The one `Secret` in `hks-capability-lab.yaml`/the Helm chart is an
  explicitly-labeled placeholder (`demo-value-not-a-real-credential`), for
  demonstrating Secret-via-env-var consumption, not a real credential.

## Troubleshooting

- **Prometheus shows zero scrape targets** — the cluster likely scopes
  Prometheus RBAC per-namespace; see `PROMETHEUS_VALIDATION.md` for the
  additive RoleBinding fix already built into `hks-capability-lab.yaml` /
  the Helm chart's `prometheus.scrapeRbac` values.
- **Ingress times out on some node IPs but not others** — check
  `externalTrafficPolicy` on the ingress controller's Service; `Local`
  (ingress-nginx's default) only answers on the node running the
  controller pod. Documented behavior, not a bug — see `NETWORKING_DECISION.md`.
- **Canary test skipped** — the canary manifest uses
  `nginx.ingress.kubernetes.io/*` annotations; it's correctly skipped (not
  failed) on clusters whose discovered IngressClass isn't `nginx`.
- **`scripts/build-multiarch.sh` only builds one architecture** — see
  "Multi-architecture support" above; this is an honest report of an
  emulation limitation, not a bug in the script.
- **Local Podman run shows "Kubernetes Not Connected"** — either no
  kubeconfig was mounted, or the mounted one is unreachable/forbidden;
  `GET /api/info` includes the specific error.

## Repository layout

```
hks-capability-lab.yaml         Core reusable app manifest (Namespace, ConfigMap,
                                 Secret, RBAC, Deployment, Services, HPA, PDB,
                                 Ingress, ServiceMonitor)
config.env.example              Copy to config.env; the only place cluster-specific
                                 values are set (or left "auto" for discovery)
run-hks-test.sh                 Interactive wizard / --all / --cleanup
sample-app/app.py               The sample app itself (stdlib-only Python, no
                                 image build or registry needed — mounted via ConfigMap)
manifests/                      Optional/demonstration resources (blue-green, canary,
                                 network-policy, storage-test, monitoring)
scripts/                        Discovery + per-capability validation scripts, plus
                                 build-image.sh / build-multiarch.sh / push-image.sh / release.sh
tests/definitions/               Machine-readable test definitions (one YAML file per
                                 category) — the source of truth every other surface
                                 (CLI, backend API, frontend, reports) reads from
backend/                        Portal backend (FastAPI) — wraps this same test-
                                 definition data behind a REST API; read-only Kubernetes
                                 discovery only, never mutates a cluster
frontend/                       Portal frontend (React/TypeScript/Tailwind)
helm/                           Helm chart + 8 example values files, packaging the
                                 same workload as hks-capability-lab.yaml
deploy/portal/                  Manifests for deploying the *portal itself* into a
                                 cluster — separate from manifests/, which is the
                                 workload the portal validates
docs/                            Architecture notes and design writeups
evidence/                       Raw kubectl/curl/Prometheus output backing every claim
00-cluster-discovery.md         What was actually found on this cluster
NETWORKING_DECISION.md          Why ingress-nginx (existing) was reused, not replaced
STORAGE_VALIDATION.md           Rook-Ceph persistence test writeup
PROMETHEUS_VALIDATION.md        Prometheus integration writeup incl. an RBAC finding
AUTOSCALER_VALIDATION.md        HPA (PASS) vs Cluster Autoscaler (infra not available)
SCHEDULING_VALIDATION.md        Affinity/anti-affinity/taints/tolerations writeup
HKS_CAPABILITY_MATRIX.md        One-table summary, evidence-linked
TEST_RESULTS.md                 Per-test-ID results (NET-*, STG-*, MON-*, AUT-*, DEP-*, ...)
HKS_PRODUCT_VALIDATION_REPORT.md Executive summary for a product/platform audience
```

## The sample application

A single-file, stdlib-only Python HTTP app (`sample-app/app.py`), run on a stock
`python:3.12-alpine` image — no custom image build or private registry
required anywhere in this suite. Its UI uses the same design tokens as the
portal frontend (`frontend/tailwind.config.js`) — same product family, no
shared build step. It exposes:

- `/` — a UI showing app/version/pod/node/namespace/container/timestamp/
  request count/CPU work performed, plus controls to generate synthetic
  CPU load (for HPA/autoscaling tests)
- `/healthz`, `/readyz`, `/livez` — health endpoints, with `/api/chaos/*`
  hooks to deliberately fail readiness/liveness or crash, for resiliency
  testing
- `/api/info` — the same data as JSON
- `/api/load?cpu=<0-100>&duration=<seconds>&concurrency=<n>` — workload generator
- `/metrics` — Prometheus exposition format (`http_requests_total`,
  `http_request_duration_seconds`, `app_cpu_work_seconds_total`,
  `app_requests_in_flight`, `app_info`)

Its version (`v1`/`v2`/`v3`) and color (`blue`/`green`/`canary`) are driven
entirely by environment variables, so rolling updates, rollback, and
blue/green/canary all just change which env vars a given pod template sets —
no image rebuild needed for any test in this suite. All data it displays
(pod name, node name, namespace, replica/health state, request counts) is
real, read from its own environment/state — never fabricated.

Keeping the Helm chart's embedded copy in sync after editing
`sample-app/app.py`:

```bash
./scripts/sync-helm-app-code.sh
```
