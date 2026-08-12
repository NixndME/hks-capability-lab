# HKS Capability Matrix

Evidence-based only. "Tested" means this lab actually exercised it against
the live cluster on 2026-08-12; nothing here is inferred from documentation.
See `TEST_RESULTS.md` for the detailed per-test writeup and `evidence/` for
raw command output.

| Capability | Supported | Tested | Result | Evidence |
|---|---|---|---|---|
| Kubernetes Deployment | Yes | Yes | PASS | `evidence/discovery-*` |
| Service ClusterIP | Yes | Yes | PASS | `evidence/access-modes-*/` NET-002 |
| NodePort | Yes | Yes | PASS | NET-003, all 4 node IPs answered |
| LoadBalancer | API only | Yes | API SUPPORTED / INFRA NOT AVAILABLE | NET-004, external IP stuck `<pending>` |
| Gateway API | Latent (Calico can enable it) | No (not activated) | NOT VALIDATED | `NETWORKING_DECISION.md` |
| Ingress | Yes (community ingress-nginx, pre-existing) | Yes | PASS | NET-005 |
| DNS (CoreDNS + Service DNS) | Yes | Yes | PASS | NET-002, `<svc>`, `<svc>.<ns>`, `<svc>.<ns>.svc`, `<svc>.<ns>.svc.cluster.local` all resolved |
| TLS (via Ingress) | Yes | Yes | PASS | HTTPS NodePort 30337, self-signed default cert |
| NetworkPolicy | Yes (Calico) | Yes | PASS | frontend→backend allowed, untrusted→backend denied |
| Horizontal Pod Autoscaler | Yes | Yes | PASS | 2→6 replicas in ~40s under load, 6→2 on cooldown |
| Cluster Autoscaler | No (no infra integration on this cluster) | Yes (exhaustion test run) | NOT AVAILABLE (infra gap, not a K8s defect) | `AUTOSCALER_VALIDATION.md`, 7 pods stuck Pending, node count never changed |
| Rolling Update | Yes | Yes | PASS | v1→v2→v3, `maxUnavailable:1/maxSurge:1` honored |
| Rollback | Yes | Yes | PASS | `kubectl rollout undo` v3→v2, reused existing ReplicaSet |
| Blue/Green | Yes (Service-selector pattern) | Yes | PASS | instant cutover + rollback, both tracks coexisted |
| Canary | Yes (ingress-nginx annotations) | Yes | PASS | 45/5 split over 50 requests (~90/10 target) |
| Persistent Storage | Yes (Rook-Ceph RBD, RWO) | Yes | PASS | marker survived pod delete/recreate |
| CSI | Yes (RBD + CephFS drivers registered) | Yes (RBD only) | PASS (RBD); CephFS/RWX not configured on this cluster | `STORAGE_VALIDATION.md` |
| Rook/Ceph | Yes, pre-existing, HEALTH_OK | Yes (read-only + isolated PVC) | PASS, not modified | `STORAGE_VALIDATION.md` |
| Prometheus | Yes, pre-existing kube-prometheus stack | Yes | PASS (after RBAC fix, see below) | `PROMETHEUS_VALIDATION.md` |
| ServiceMonitor | CRD present, selectors match-all | Yes | PASS, but required a namespace-scoped RBAC grant not present by default | `PROMETHEUS_VALIDATION.md` |
| PodMonitor | CRD present | No (not exercised) | NOT VALIDATED | — |
| Pod Rescheduling | Yes | Yes | PASS | deleted pod replaced automatically, Service stayed reachable |
| Scheduling Constraints (requests/limits) | Yes | Yes | PASS | `Insufficient cpu` correctly blocked scheduling |
| Node Affinity | Yes | Yes | PASS | required affinity pinned pod to exact node |
| Pod Anti-Affinity | Yes (soft) | Yes | PASS with caveat | preferred anti-affinity influenced but did not guarantee even spread under contention |
| Topology Spread | Yes (soft) | Yes | PASS with caveat | same caveat as anti-affinity |
| Taints/Tolerations | Yes | Yes | PASS | untainted-pod stayed Pending on control-plane, tolerated pod scheduled there |
| Network Isolation (default-deny) | Yes (Calico) | Yes | PASS | see NetworkPolicy row |
| Readiness Probe | Yes | Yes | PASS | pod left/rejoined Service endpoints correctly |
| Liveness Probe | Yes | Yes | PASS | container restarted after 3 consecutive failures |
| RBAC | Yes | Yes | PASS | scoped ServiceAccount/Role/RoleBinding created and used |
