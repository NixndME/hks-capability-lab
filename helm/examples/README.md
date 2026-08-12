# Helm example values

Each file is a small override on top of `../hks-capability-lab/values.yaml`
for one deployment scenario. All eight are validated with
`helm template hks-lab ../hks-capability-lab -f <file>` as part of this
repo's Helm work (see `../hks-capability-lab/README.md` for the base chart).

| File | Scenario |
|---|---|
| `values-default.yaml` | Chart defaults (ClusterIP + NodePort + Ingress on the cluster's default class) |
| `values-nodeport.yaml` | NodePort-only, Ingress disabled |
| `values-loadbalancer.yaml` | LoadBalancer Service (API-level only unless the cluster has LB infra) |
| `values-ingress.yaml` | Ingress pinned to `nginx`, TLS enabled |
| `values-gateway.yaml` | Gateway API routing against an existing GatewayClass |
| `values-storage.yaml` | PVC-backed persistence at `/data` |
| `values-prometheus.yaml` | ServiceMonitor + the additive Prometheus scrape RBAC grant |
| `values-full.yaml` | Every optional feature on at once (for exercising the whole chart, not a production baseline) |

```bash
helm install hks-lab ../hks-capability-lab -f values-ingress.yaml
```
