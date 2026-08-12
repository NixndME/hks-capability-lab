# hks-capability-lab (Helm chart)

Packages the same workload as `../../hks-capability-lab.yaml` (Namespace,
ConfigMap-embedded app source, Secret, ServiceAccount/Role/RoleBinding,
Deployment, ClusterIP + NodePort Services, HPA, PDB, Ingress) as a
parameterized Helm chart, plus optional NetworkPolicy, PVC persistence, and
Gateway API routing. Raw YAML and Helm are both fully supported deployment
paths — this chart does not replace `hks-capability-lab.yaml`.

## Install

```bash
helm install hks-lab helm/hks-capability-lab \
  --set ingress.host=hks-demo.yourdomain.example
```

## Lint / template / package (no cluster needed)

```bash
helm lint helm/hks-capability-lab
helm template hks-lab helm/hks-capability-lab
helm package helm/hks-capability-lab
```

## Keeping the embedded app source in sync

The chart embeds `sample-app/app.py` as a ConfigMap via `.Files.Get`, which
is scoped to the chart directory and can't read outside it. After editing
`sample-app/app.py`, resync the chart's copy before templating/packaging:

```bash
./scripts/sync-helm-app-code.sh
```

## Notable values

| Key | Default | Notes |
|---|---|---|
| `namespace.create` | `true` | set `false` to install into a namespace you manage yourself |
| `ingress.className` | `""` | empty = cluster default IngressClass |
| `persistence.storageClassName` | `""` | empty = cluster default StorageClass |
| `gateway.enabled` | `false` | requires an existing GatewayClass; this chart never enables Gateway API itself |
| `prometheus.serviceMonitor.enabled` | `false` | enable only after confirming `kubectl get crd servicemonitors.monitoring.coreos.com` |
| `prometheus.scrapeRbac.enabled` | `false` | additive namespace-scoped RBAC grant for the cluster's existing Prometheus ServiceAccount — see `../../PROMETHEUS_VALIDATION.md` |
| `networkPolicy.enabled` | `false` | requires a NetworkPolicy-enforcing CNI (e.g. Calico) |

See `../examples/` for ready-made `values-*.yaml` files per scenario and
`values.schema.json` for the full validated shape.
