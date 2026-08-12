# Public YAML artifacts

Customer-facing Kubernetes manifests for the [hks-experience](../hks-experience/)
guided journey. Every file here is:

- **Human-readable** — plain Kubernetes objects, no `envsubst`, no
  templating, no placeholders you can't see.
- **Self-contained** — `kubectl apply -f <file>` and nothing else. No
  `git clone`, no repository checkout, no build step.
- **Stably hosted** — committed to Git so each file has a permanent raw
  GitHub URL:
  `https://raw.githubusercontent.com/<owner>/<repo>/<branch>/yaml/<file>`
  (the `hks-experience` portal derives `<owner>/<repo>` from this repo's own
  `git remote get-url origin`, and `<branch>` from `PUBLIC_ARTIFACT_BRANCH` —
  see `hks-experience/backend/app/config.py`).

This directory is **separate from [`../manifests/`](../manifests/)**, which
belongs to the existing CLI validator (`../run-hks-test.sh`) and uses
`envsubst`-templated placeholders (`${NAMESPACE}`, `${STORAGE_CLASS}`, …) —
appropriate for a script-driven workflow, wrong for a customer copy-pasting
a `kubectl apply -f <url>` command by hand. Everything here uses the same
concrete `hks-capability-lab` namespace and the same resource names the
validator and the guided journey's backend executor
(`hks-experience/backend/app/shim.sh`) already use, so a step's "Verify"
button keeps working however you applied the underlying resource.

Not every guided-journey step has a file here — only ones that are genuinely
Kubernetes resource deployments. Steps that are an application interaction
(generate CPU/memory load), a discovery/inspection action (scheduling,
resiliency's pod-kill), or an external DNS instruction (Public Domain) don't
get one; see `hks-experience/workflows/README.md` for how each step is
classified.

| # | File | Creates | Depends on |
|---|------|---------|------------|
| 01 | `01-namespace.yaml` | 1 Namespace (`hks-capability-lab`) | — |
| 02 | `02-application.yaml` | ConfigMap, Secret, ServiceAccount, Role, RoleBinding, Deployment, Service (ClusterIP), PodDisruptionBudget | 01 |
| 03 | `03-clusterip.yaml` | Service (ClusterIP) — same object as in 02, standalone for the ClusterIP teaching step | 01, 02 |
| 04 | `04-nodeport.yaml` | Service (NodePort) | 01, 02 |
| 05 | `05-loadbalancer.yaml` | Service (LoadBalancer) | 01, 02 |
| 06 | `06-ingress.yaml` | Ingress | 01, 02 |
| 07 | `07-gateway.yaml` | Gateway + HTTPRoute (Gateway API) | 01, 02 |
| 08 | `08-hpa.yaml` | HorizontalPodAutoscaler | 01, 02 |
| 09 | `09-prometheus.yaml` | PrometheusRule (optional alerting) | 01, 10 |
| 10 | `10-servicemonitor.yaml` | ServiceMonitor | 01, 02 |
| 11 | `11-storage.yaml` | PersistentVolumeClaim, Deployment (storage test) | 01 |
| 12 | `12-network-policy.yaml` | 3 Deployments/Services + 2 NetworkPolicies | 01 |
| 13 | `13-rolling-update-v2.yaml` | Deployment `hks-lab-app` at `APP_VERSION=v2` | 01, 02 |
| 14 | `14-rolling-update-v3.yaml` | Deployment `hks-lab-app` at `APP_VERSION=v3` | 01, 02 |
| 15 | `15-blue-green.yaml` | 2 Deployments (blue/green) + 1 traffic-switching Service | 01, 02 |
| 16 | `16-canary.yaml` | Deployment + Service + weighted Ingress | 01, 02, 06 |
| 17 | `17-resiliency.yaml` | PodDisruptionBudget — same object as in 02, standalone for reference | 01, 02 |

Every file's own header comment states what it creates, what it depends on,
the exact `kubectl apply -f` command, and how to verify it worked — that
same content is what the guided-journey UI shows in its "What this YAML
creates" / "Run this" / "Verify" panels, sourced live from these files (see
`hks-experience/backend/app/public_artifacts.py`), never duplicated by hand.

## Validating

```bash
for f in yaml/*.yaml; do kubectl apply --dry-run=server -f "$f" || echo "FAILED: $f"; done
```

(`--dry-run=server` round-trips through the API server's admission chain
without persisting anything — safe to run against a live cluster, and the
only way to validate CRD-backed kinds like `ServiceMonitor`/`Gateway`
without vendoring their schemas locally.)
