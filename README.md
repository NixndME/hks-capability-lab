# HKS Capability Lab

Validates what an HPE Morpheus HKS Kubernetes cluster actually supports —
networking, storage, scaling, observability, deployment lifecycle,
security, resiliency — against a realistic sample workload, with
evidence-backed results instead of assumptions.

**Docker Hub:** `docker.io/nixndme/hks-capability-lab` · **Repo:** two things live here, see below.

## Contents

- [The 60-second version](#the-60-second-version)
- [Quick start](#quick-start)
- [How this actually works end-to-end](#how-this-actually-works-end-to-end) ← start here if you're not sure what the portal does vs. what the CLI does
- [What gets validated](#what-gets-validated)
- [Repository layout](#repository-layout)
- [Deployment options: raw YAML vs. Helm](#deployment-options-raw-yaml-vs-helm)
- [Container images](#container-images)
- [Building it yourself](#building-it-yourself)
- [Configuration](#configuration)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

---

## The 60-second version

Two things live in this repo:

1. **The HKS Capability Portal** (`frontend/` + `backend/`) — a web UI for
   browsing what's validated, viewing/copying the exact YAML or Helm
   commands for each capability, checking cluster connection status, and
   generating reports.
2. **The HKS Sample Application** (`sample-app/app.py`) — the realistic
   workload that gets deployed and exercised. The portal is the reference
   material; the sample app is the thing actually running on your cluster.

**The portal browses and documents. It does not run kubectl/helm against
your cluster for you.** The thing that actually executes validations
end-to-end is `run-hks-test.sh` (or you, copy-pasting commands from the
portal). See [How this actually works](#how-this-actually-works-end-to-end)
— this distinction is the most important thing to understand before using
either.

## Quick start

Pick one:

| I want to... | Do this |
|---|---|
| **Browse capabilities, copy commands/YAML/Helm** — no cluster needed | `podman run --rm -p 8080:8080 docker.io/nixndme/hks-capability-lab:latest` → open http://localhost:8080 |
| **Browse + see live cluster connection status** (context, K8s version, node count) | Add `-v ~/.kube:/home/hkslab/.kube:ro` to the command above |
| **Actually run the validations against my cluster** | `./run-hks-test.sh` (clone this repo, needs `kubectl`+`envsubst`, no container needed) — see below |

## How this actually works end-to-end

This is the part that matters if you're a platform engineer with your own
HKS cluster wondering "okay, concretely, what do I *do*":

```
 1. Get a working kubeconfig for your cluster (kubectl already configured)
          │
          ▼
 2. Either...
      (a) run the portal locally to browse first             (b) skip straight to the CLI
          podman run -p 8080:8080 \                               git clone this repo
            -v ~/.kube:/home/hkslab/.kube:ro \                    cd hks-capability-lab
            docker.io/nixndme/hks-capability-lab:latest            cp config.env.example config.env
          open http://localhost:8080                               ./run-hks-test.sh
          Sidebar shows "Cluster Connection: Connected"
          if your kubeconfig is reachable (read-only check —
          the portal never runs kubectl/helm for you)
          │
          ▼
 3. Open a capability (e.g. "HPA scale-up") in the portal.
    You get: description, why it matters, the EXACT commands
    used to validate it, success conditions, and links to the
    underlying YAML/Helm artifacts. Copy/download buttons on
    every command block.
          │
          ▼
 4. Run those commands yourself against your cluster
    (kubectl apply / helm install / curl / etc — same commands
    run-hks-test.sh runs automatically), OR just run
    ./run-hks-test.sh --all and let it execute every capability
    in sequence, non-interactively, against whatever cluster
    your current kubectl context points at.
          │
          ▼
 5. Check results: run-hks-test.sh prints PASS/FAIL/SKIP per
    capability and writes evidence/test-run-<timestamp>.log.
    The portal's Reports page (docs/validation/ + tests/definitions/)
    shows the same result set for the reference cluster this
    suite was built and validated against.
          │
          ▼
 6. ./run-hks-test.sh --cleanup removes only what the suite
    created (demo blue/green, canary, network-policy, storage-
    test resources) — the core app and your cluster's existing
    workloads are never touched.
```

**In short:** the portal (hosted or local-via-Podman) is a reference/
browsing tool — it tells you exactly what to run and what to expect,
including live cluster-connection status in local mode. `run-hks-test.sh`
is what actually runs kubectl/helm against your cluster, whether you use
the portal at all or not. They read the same underlying
[test definitions](tests/definitions/), so neither one can drift from what
the other claims.

### Hosted vs. local mode

| | Hosted (`https://hks.nixndme.com`) | Local (Podman) |
|---|---|---|
| Cluster access | **Never** — no kubeconfig upload, ever | Optional, **read-only** discovery only if you mount `~/.kube` |
| What you get | Copyable YAML/Helm/kubectl commands, docs, manual verification workflow | Same, plus live "Cluster Connection: Connected/Not Connected" status |
| Runs tests for you | No | No — read-only discovery only (see `backend/app/k8s.py`); use `run-hks-test.sh` for execution |

## What gets validated

- **Networking:** ClusterIP, NodePort, LoadBalancer (API vs. infrastructure), Ingress/Gateway API, TLS, NetworkPolicy, DNS
- **Workload management:** rolling updates, rollback, blue/green, canary, scheduling (affinity, taints/tolerations, resource requests)
- **Autoscaling:** HPA and Cluster Autoscaler (distinguishing "not supported" from "supported but infra unavailable")
- **Storage:** dynamic provisioning, persistence across restarts, Rook/Ceph integration (read-only)
- **Observability:** Prometheus Operator / ServiceMonitor integration, without touching the existing Prometheus install
- **Resiliency:** readiness/liveness probes, pod rescheduling, availability during disruption

34 capabilities tracked in [`tests/definitions/`](tests/definitions/), each with a result of
`PASS` / `FAIL` / `NOT_AVAILABLE` (infra gap) / `NOT_VALIDATED` (in scope, not yet exercised) —
see [`tests/definitions/README.md`](tests/definitions/README.md) for why those are never collapsed into a single pass/fail.
Full narrative writeups and raw evidence: [`docs/validation/`](docs/validation/) and [`evidence/`](evidence/).

This suite never fabricates a PASS — see
[`docs/validation/AUTOSCALER_VALIDATION.md`](docs/validation/AUTOSCALER_VALIDATION.md) for what an honest
`NOT_AVAILABLE` looks like, and never deletes/modifies existing cluster
workloads, StorageClasses, or the existing Prometheus/Ingress install (see
[`docs/validation/NETWORKING_DECISION.md`](docs/validation/NETWORKING_DECISION.md)).

## Repository layout

```
README.md, Containerfile, compose.yaml   Top-level entry points
run-hks-test.sh, config.env.example      CLI — the thing that executes validations
hks-capability-lab.yaml                  Core app manifest (raw YAML deployment path)
manifests/                               Optional demo manifests (blue/green, canary, network-policy, storage-test)
scripts/                                 Discovery, per-capability validation, and build/release scripts
sample-app/app.py                        The sample application (stdlib-only Python, no image build needed)

backend/                                 Portal API (FastAPI) — read-only cluster discovery + serves tests/definitions/
frontend/                                Portal UI (React/TypeScript/Tailwind)
helm/                                    Helm chart + 8 example values files
deploy/portal/                           Manifests for deploying the PORTAL itself (not the sample workload)

tests/definitions/                       Machine-readable capability definitions — the shared source of truth
docs/validation/                         Narrative validation writeups (per-capability results, decisions, executive summary)
docs/                                    Architecture notes
evidence/                                Raw kubectl/curl/Prometheus output backing every claim
```

## Deployment options: raw YAML vs. Helm

Both fully supported, neither replaces the other — pick whichever fits your workflow:

```bash
# Raw YAML
envsubst < hks-capability-lab.yaml | kubectl apply -f -

# Helm
helm install hks-lab helm/hks-capability-lab -f helm/examples/values-ingress.yaml
```

See [`helm/hks-capability-lab/README.md`](helm/hks-capability-lab/README.md) for chart details and
[`helm/examples/`](helm/examples/) for 8 ready-made scenarios (NodePort, LoadBalancer, Ingress, Gateway API, storage, Prometheus, everything-on).

## Container images

```bash
podman run --rm -p 8080:8080 docker.io/nixndme/hks-capability-lab:latest
```

Published on Docker Hub: `docker.io/nixndme/hks-capability-lab:latest` and `:1.0.0`.

| Tag | Architecture | Status |
|---|---|---|
| `latest`, `1.0.0` | `linux/amd64` | Built, smoke-tested, and pulled fresh from Docker Hub to confirm |
| — | `linux/arm64` | **Not published yet.** Cross-building it on this host fails even with a correctly-registered host-level `binfmt_misc` QEMU handler (`podman run --privileged --platform linux/arm64 alpine uname -m` still errors `Exec format error`) — this looks like a rootless-Podman limitation beyond what `qemu-user-static-binfmt` alone fixes, not a missing package. Building `linux/arm64` on an actual ARM64 host, or via `sudo podman build` with real root, should work; `scripts/build-multiarch.sh` is ready to pick it up once that's available. |

`scripts/build-multiarch.sh` always reports exactly which architectures it actually built and runtime-tested on a given run — see its output rather than assuming both are current.

## Building it yourself

Podman throughout (not Docker Desktop):

```bash
./scripts/build-image.sh              # single-arch (host), builds + smoke-tests
./scripts/build-multiarch.sh          # amd64 + arm64, manifest list
./scripts/release.sh --dry-run        # fast, non-mutating checks only
./scripts/release.sh                  # full pipeline: YAML/Helm/frontend/backend checks, build, smoke test — no push
podman login docker.io && ./scripts/push-image.sh <tag> [--manifest]   # push — always separate, always confirmed interactively
```

## Configuration

Nothing hard-codes `hks.nixndme.com` or any cluster-specific value into
application logic — everything below is a default, overridden via env
vars/`config.env`:

| Variable | Default | Where |
|---|---|---|
| `PUBLIC_BASE_URL` / `PORTAL_DOMAIN` | `https://hks.nixndme.com` (hosted) / `http://localhost:8080` (local) | `backend/app/config.py` |
| `PORTAL_MODE` | `local` | `hosted` disables all kubeconfig access, unconditionally |
| `NAMESPACE`, `TEST_HOST`, `STORAGE_CLASS`, `INGRESS_CLASS` | see `config.env.example` | CLI / raw YAML |
| chart values | see `helm/hks-capability-lab/values.yaml` | Helm |

## Security

- Hosted mode never requests, accepts, or stores a kubeconfig.
- Local mode's kubeconfig mount is read-only by default; the backend only issues `get`/`list` calls and degrades to "not connected" on any failure — never crashes, never mutates.
- The browser only ever talks to this project's own backend, never to Kubernetes directly.
- No Kubernetes credentials are exposed to frontend JavaScript or written to browser storage.
- Runtime container user is non-root (`hkslab`, uid 10001).
- The one `Secret` in `hks-capability-lab.yaml`/the Helm chart is an explicitly-labeled placeholder, not a real credential.

## Troubleshooting

- **Prometheus shows zero scrape targets** — the cluster likely scopes Prometheus RBAC per-namespace; see [`docs/validation/PROMETHEUS_VALIDATION.md`](docs/validation/PROMETHEUS_VALIDATION.md) for the additive RoleBinding fix already built into `hks-capability-lab.yaml` / the Helm chart's `prometheus.scrapeRbac`.
- **Ingress times out on some node IPs but not others** — check `externalTrafficPolicy` on the ingress controller's Service; `Local` (ingress-nginx's default) only answers on the node running the controller pod. Documented, not a bug — see [`docs/validation/NETWORKING_DECISION.md`](docs/validation/NETWORKING_DECISION.md).
- **Canary test skipped** — uses `nginx.ingress.kubernetes.io/*` annotations; correctly skipped (not failed) on clusters whose IngressClass isn't `nginx`.
- **Portal shows "Kubernetes Not Connected" locally** — either no kubeconfig was mounted, or it's unreachable/forbidden; `GET /api/info` includes the specific error.
- **Portal doesn't seem to "do" anything when I click a test** — correct, by design; it shows you what to run, it doesn't run it. Use `run-hks-test.sh` for automated execution, or copy the commands shown.

---

Full per-capability results and executive summaries: [`docs/validation/`](docs/validation/) · Architecture notes: [`docs/INITIAL_ARCHITECTURE_ASSESSMENT.md`](docs/INITIAL_ARCHITECTURE_ASSESSMENT.md)
