# HKS Capability Lab — Guided Experience

A **separate product**, built beside the existing validator
(`../run-hks-test.sh`, `../hks-capability-lab.yaml`, `../scripts/`,
`../backend/` + `../frontend/`) — not a replacement for it. That system is
untouched; this one drives it, step by step, from a guided customer-facing
UI instead of a menu or a flat dashboard.

## What this is (and isn't)

- **Is:** a 23-step guided journey. Welcome → one capability at a time →
  explain → deploy → verify → observe → understand → next. Every step can
  be skipped and revisited. Only the final Summary screen shows aggregate
  results.
- **Isn't:** "run everything and show 26/28 PASS" on load. There is no
  bulk-run entrypoint anywhere in this app, by design.

## Running the portal vs. testing your cluster

Two completely separate concerns:

- **Running this portal** — Docker/Podman only matter here (see "Local
  Installation" below), or the hosted SaaS at `https://hks.nixndme.com`.
- **Testing your Kubernetes/HKS cluster** — the guided journey never asks
  you to use Docker or Podman for a Kubernetes deployment step. Every
  Kubernetes action in the journey is `kubectl apply -f <a public
  raw-GitHub YAML URL>` (see [`../yaml/`](../yaml/)), `helm install`, your
  browser, or your DNS provider — nothing else. If a step's error message
  ever mentions your container runtime, that's a bug; file it.

## Local Installation

Podman and Docker both work — the image and flags are identical either way
(only the CLI name changes):

```bash
# Podman
podman run --rm -p 8080:8080 docker.io/nixndme/hks-capability-lab-experience:latest

# Docker
docker run --rm -p 8080:8080 docker.io/nixndme/hks-capability-lab-experience:latest
```

`open http://localhost:8080` — browse-only, no cluster access, in either case.

With real execution against your cluster (read-only discovery **and**
step-by-step actions — deploy, verify, generate load, kill a pod, switch
traffic — all reusing the existing validator's proven commands, never new
untested mutation logic):

```bash
# Podman
podman run --rm -p 8080:8080 \
  -v ~/.kube:/home/hksexp/.kube:ro \
  docker.io/nixndme/hks-capability-lab-experience:latest

# Docker
docker run --rm -p 8080:8080 \
  -v ~/.kube:/home/hksexp/.kube:ro \
  docker.io/nixndme/hks-capability-lab-experience:latest
```

(Runtime user is non-root `hksexp`, home `/home/hksexp` — not `/root`, for
both Podman and Docker.)

Hosted mode (`PORTAL_MODE=hosted`) disables all execution unconditionally
— same rule as the existing portal.

## How "real execution" actually works

Every "Run / Verify" button calls the backend, which calls
[`backend/app/shim.sh`](backend/app/shim.sh) — a thin wrapper that
`source`s **the existing validator's own `../scripts/lib.sh`**
(`render_apply`, `wait_rollout`, `has_prometheus_operator`, etc.) and adds
small, step-addressable `action_*` functions around those exact primitives.
`scripts/lib.sh` itself is never modified. This was a deliberate design
choice over calling `../scripts/validate-*.sh` directly: those scripts are
monolithic per-category (e.g. one script tests NodePort *and* LoadBalancer
*and* Ingress together) and aren't individually callable per guided step —
modifying them to be so was explicitly out of scope ("do not rewrite the
test engine").

Every action was actually run against a live HKS cluster during
development (not just unit-tested) — cluster discovery, namespace
creation, app deployment, HPA + real CPU load (replica count genuinely
climbed), rolling update, blue/green traffic switch, storage persistence,
pod-kill resiliency, and NetworkPolicy allow/deny. One real bug was found
and fixed in the process (a wrong pod label selector in the storage-test
action) — see the project's final report for the full list of what was and
wasn't verified live.

## The sample workload: HKS Demo Workload

[`sample-app/app.py`](sample-app/app.py) — a separate, purpose-built
application (not the existing validator's `../../sample-app/app.py`),
branded "HKS Demo Workload", with Overview/Activity/Performance/Runtime
tabs and a CPU+memory workload generator. All figures are real
(`resource.getrusage` for CPU/memory, actual request timing) — it never
reports a replica count or traffic split, since a single pod can't
honestly know that; anything cluster-wide comes from the backend's
`/api/live/*` endpoints instead (which do have cluster API access).

The "Deploy the Sample Application" step's **Run / Verify** button reuses
the existing validator's entire proven Deployment/Service/HPA/RBAC
infrastructure from `../hks-capability-lab.yaml` via `shim.sh` — only the
ConfigMap's embedded app source is swapped for this new one. The step's
**copy-pasteable `kubectl apply -f <url>` command**, shown to the customer
above that button, applies the equivalent public manifest,
[`../yaml/02-application.yaml`](../yaml/02-application.yaml) — same
resource names/namespace either way, so Verify works no matter which path
you took. One workload, two ways to operate it, one set of resource names.

## Public YAML artifacts

The guided journey never asks a customer to `git clone` this repository or
run `envsubst`. Every step that's a genuine Kubernetes resource deployment
points at a plain, human-readable manifest committed under
[`../yaml/`](../yaml/) (separate from `../manifests/`, which belongs to the
existing CLI validator and uses `envsubst` placeholders) — with a stable
raw GitHub URL a customer can `kubectl apply -f` directly:

```
https://raw.githubusercontent.com/<owner>/<repo>/<ref>/yaml/<file>
```

`<owner>/<repo>` is never hard-coded: `backend/app/config.py` derives it
from this checkout's own `git remote get-url origin` at runtime (dev), or
from `PUBLIC_GITHUB_OWNER`/`PUBLIC_GITHUB_REPO` env vars baked in at
container build time (production, since a built image never contains
`.git` — see `.containerignore`). `<ref>` defaults to the current git
branch, overridable via `PUBLIC_ARTIFACT_REF` — pin it to a release tag
(e.g. `v1.0.0`) for reproducible production artifacts. The whole base URL
can also be overridden directly via `PUBLIC_GITHUB_RAW_BASE_URL`. See
[`../yaml/README.md`](../yaml/README.md) for the full file list and
[`backend/app/public_artifacts.py`](backend/app/public_artifacts.py) for
how each step's "What this YAML creates" / View / Copy / Download / Open
Raw GitHub panel gets its content — always read live from `../yaml/`,
never duplicated by hand into the workflow files.

Helm works the same way without cloning: `GET
/api/public-yaml/helm-chart.tgz` packages
[`../helm/hks-capability-lab`](../helm/hks-capability-lab) live via `helm
package`, so the "Download Chart" button in the journey's Helm tab hands
back a single installable archive.

## Structure

```
backend/       FastAPI: workflow engine, session progress, shim.sh executor, live-poll endpoints
frontend/      React/TS/Tailwind: Welcome, Journey (sidebar+stepper), Summary
sample-app/    HKS Demo Workload (separate from ../sample-app/app.py)
workflows/     23-step journey content (YAML, one file per category) -- see workflows/README.md
charts/        Reuses ../helm/hks-capability-lab -- not duplicated, see charts/README.md
artifacts/     Live-generated bundle.zip (whole-repo YAML+Helm download) -- see artifacts/README.md
../yaml/       Customer-facing public manifests with stable raw GitHub URLs -- see ../yaml/README.md
scripts/       build-multiarch.sh (Podman) + build-multiarch-docker.sh (Docker Buildx) for THIS image
Containerfile  Separate image: docker.io/nixndme/hks-capability-lab-experience
```

## Image

`docker.io/nixndme/hks-capability-lab-experience` — deliberately a
different repository from the existing validator's
`docker.io/nixndme/hks-capability-lab`; neither overwrites the other.

| Tag | Architecture | Status |
|---|---|---|
| `latest`, `1.1.0`, `1.0.0` | `linux/amd64`, `linux/arm64` | Published. Built, multi-arch manifest pushed, smoke-tested, and verified on both architectures. |

## Building multi-arch (`linux/amd64` + `linux/arm64`)

Two scripts exist because the two tools behave differently on cross-arch
builds — pick whichever you have:

### With Docker (recommended for publishing arm64)

```bash
docker login docker.io
./hks-experience/scripts/build-multiarch-docker.sh 1.0.0 --push
```

Uses `docker buildx` with a `docker-container` builder, which bundles its
own QEMU emulation for foreign architectures — this is the path most
likely to actually produce a working `linux/arm64` image. Requires the
buildx plugin (`docker buildx version` — ships with Docker Desktop, or
install `docker-buildx-plugin` on Linux).

### With Podman

```bash
podman login docker.io
./hks-experience/scripts/build-multiarch.sh 1.0.0
# then, only if it reports both architectures built:
podman manifest push --all docker.io/nixndme/hks-capability-lab-experience:1.0.0 \
  docker://docker.io/nixndme/hks-capability-lab-experience:1.0.0
```

**Known limitation, reported honestly rather than worked around:** on this
project's original development host, rootless Podman could not produce a
working `linux/arm64` build even after registering `qemu-user-static-binfmt`
at the host kernel level (`podman run --privileged --platform linux/arm64
alpine uname -m` still failed with `Exec format error`) — this looks like a
rootless-Podman-specific limitation, not a missing package, and is why the
Docker Buildx path above exists as the primary route to a real multi-arch
publish. `build-multiarch.sh` always reports exactly which architectures it
actually built and runtime-tested on a given run rather than assuming —
trust its output over this table if they disagree.
