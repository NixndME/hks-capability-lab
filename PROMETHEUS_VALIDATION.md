# Prometheus Validation

The cluster already runs a full kube-prometheus stack. **Nothing about the
existing Prometheus, Alertmanager, or Grafana deployment was modified.**
This validation only adds a ServiceMonitor/PrometheusRule in the lab's own
namespace and (see below) a small, additive RBAC grant so Prometheus's
existing ServiceAccount can see that namespace.

## Discovered configuration

| Item | Value |
|---|---|
| Prometheus namespace | `monitoring` |
| Prometheus object | `k8s` (2 replicas, StatefulSet `prometheus-k8s`) |
| Prometheus version | 3.10.0 |
| Prometheus Service | `prometheus-k8s.monitoring.svc`, ports `9090` (API/UI), `8080` |
| Prometheus URL (via port-forward) | `kubectl -n monitoring port-forward svc/prometheus-k8s 9090:9090` → http://localhost:9090 |
| Grafana | `grafana.monitoring.svc:3000` (not modified; not exercised further by this lab) |
| Prometheus Operator | Present, 2/2 |
| ServiceMonitor CRD | Available (`servicemonitors.monitoring.coreos.com`) |
| PodMonitor CRD | Available (`podmonitors.monitoring.coreos.com`), not used by this lab |
| PrometheusRule CRD | Available, used for one demo alert |
| `serviceMonitorSelector` / `serviceMonitorNamespaceSelector` on the `Prometheus` CR | Both `{}` (match everything, all namespaces) |
| `ruleSelector` / `ruleNamespaceSelector` | Both `{}` (match everything, all namespaces) |
| External/private access | No Ingress/Route exists for Prometheus or Grafana; port-forward is the only path from outside the cluster today |

Because the selectors are all `{}`, **any** ServiceMonitor/PrometheusRule
anywhere in the cluster is eligible for pickup — labels don't need to match
a specific release name on this install.

## Finding: ServiceMonitor CRD support ≠ automatic discovery in a new namespace

Applying the lab's `ServiceMonitor` initially produced **zero scrape
targets**, even though the object was accepted and the selectors matched.

Root cause (confirmed via `prometheus-k8s-0`'s `prometheus` container logs):

```
User "system:serviceaccount:monitoring:prometheus-k8s" cannot list resource
"endpoints"/"services"/"pods" in API group "" in the namespace "hks-capability-lab"
```

This cluster's kube-prometheus install does **not** grant Prometheus a
cluster-wide read `ClusterRole` for Services/Endpoints/Pods. Instead it uses
a namespace-scoped `Role`/`RoleBinding` pattern, pre-applied only for
`default`, `kube-system`, and `monitoring`:

```
$ kubectl get rolebinding -A | grep prometheus-k8s
default      prometheus-k8s          -> Role prometheus-k8s
kube-system  prometheus-k8s          -> Role prometheus-k8s
monitoring   prometheus-k8s          -> Role prometheus-k8s
```

**This is "capability exists but a prerequisite is missing," not "platform
doesn't support it."** ServiceMonitor-based discovery is fully functional —
it just needs the same namespaced Role/RoleBinding pattern extended to any
new application namespace, exactly as this platform already does for its
three pre-authorized namespaces.

**Fix applied** (now part of the reusable `hks-capability-lab.yaml`): a
`Role`/`RoleBinding` in `hks-capability-lab` granting
`get/list/watch` on `services`, `endpoints`, `pods` to
`system:serviceaccount:${PROMETHEUS_NAMESPACE}:${PROMETHEUS_SERVICEACCOUNT}`
— i.e. the exact same three verbs/resources as the platform's own
`prometheus-k8s` Role, mirrored into the new namespace. This is purely
additive: it does not touch the `monitoring` namespace, the Prometheus CR,
or any existing RoleBinding. `run-hks-test.sh` discovers the Prometheus
namespace/ServiceAccount live (`kubectl get prometheus -A`) rather than
hard-coding `monitoring`/`prometheus-k8s`.

After applying the Role/RoleBinding, both `hks-lab-app` pods appeared as
`up` scrape targets within one Prometheus Operator reconcile + config-reload
cycle.

## Finding: ServiceMonitor selector should target one Service, not a shared label

The first working version of the ServiceMonitor selected on
`app.kubernetes.io/name: hks-lab-app`, a label present on **both**
`hks-lab-app` (ClusterIP) and `hks-lab-app-nodeport` (NodePort) — both
Services select the same pods, so Prometheus discovered the same 2 pod
endpoints twice, under two different `job` labels
(`hks-lab-app` and `hks-lab-app-nodeport`), double-scraping every pod.
Fixed by adding a dedicated `hks-capability-lab/metrics: primary` label to
only the ClusterIP Service and pointing the ServiceMonitor's selector at
that label instead. Confirmed via `/api/v1/targets`: exactly 2 targets
(one per pod), single job, both `up`.

## Observed operational note

After changing the ServiceMonitor's `spec.selector`, Prometheus Operator
regenerated the underlying config Secret within seconds (confirmed via
`kubectl -n monitoring get secret prometheus-k8s -o jsonpath=...`), but the
running Prometheus process did not pick it up until the **kubelet's
periodic Secret-volume sync** caught up (observed delay: up to ~90 seconds
in `config-reloader` logs) — this is standard Kubernetes Secret-volume
propagation behavior, not a defect. `run-hks-test.sh` waits accordingly
before asserting scrape success.

## Result

| Check | Result |
|---|---|
| ServiceMonitor CRD accepted | PASS |
| PrometheusRule CRD accepted | PASS |
| Scrape target discovered | PASS (after namespace RBAC grant — documented above) |
| Target health | `up` for both pods |
| Application metrics visible in Prometheus | PASS — `app_info`, `http_requests_total`, `http_request_duration_seconds_*`, `app_cpu_work_seconds_total`, `app_requests_in_flight`, plus standard `up` |
| Double-scrape avoided | PASS (after selector fix) |

## Useful queries

```promql
up{namespace="hks-capability-lab"}
app_info
sum(rate(http_requests_total[5m])) by (path, status)
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
app_cpu_work_seconds_total
app_requests_in_flight
ALERTS{alertname="HksLabAppTargetDown"}
```

## Access

```bash
kubectl -n monitoring port-forward svc/prometheus-k8s 9090:9090
# http://localhost:9090
```

No public/private network path to Prometheus exists beyond port-forward —
there is no Ingress/Route for it, and this lab intentionally does not add
one (out of scope: exposing the existing Prometheus is a platform-team
decision, not something this test suite should do unilaterally).

Full evidence: `evidence/prometheus/`.
