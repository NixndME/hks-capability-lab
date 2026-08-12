# HKS Product Validation Report

**Cluster under test:** self-hosted HKS instance, 4 nodes (1 control-plane +
3 workers), kubeadm-provisioned on local KVM/libvirt VMs, Kubernetes
v1.35.7. **Date:** 2026-08-12.

## Executive Summary

This HKS cluster successfully demonstrated the full core Kubernetes
capability set a platform team would expect: workload scheduling, rolling
updates and rollback, horizontal pod autoscaling, persistent storage backed
by a healthy Rook/Ceph install, NetworkPolicy enforcement via Calico,
integration with an existing Prometheus/Grafana observability stack, and
both blue/green and canary release patterns using only the ingress
controller already present — no additional infrastructure was installed to
achieve any of this.

Two gaps were found and are worth platform-team attention:

1. **Cluster Autoscaler has no infrastructure integration on this
   particular instance.** HPA (pod-level scaling) works correctly; node-level
   scaling does not exist here because this is a static VM cluster with no
   node-pool/cloud integration wired up. This is an infrastructure-layer
   gap specific to this deployment, not a Kubernetes or HKS platform defect.
2. **Prometheus's RBAC is scoped per-namespace**, not cluster-wide — new
   application namespaces are invisible to Prometheus's ServiceMonitor
   discovery until an admin (or this test suite) grants the same
   Role/RoleBinding pattern already used for `default`/`kube-system`/
   `monitoring`. This is a one-time, low-effort onboarding step worth
   documenting for every new team/namespace, or worth converting to a
   cluster-wide grant if that tradeoff is acceptable for this platform.

Everything else tested passed cleanly, several times, with reproducible
automation left behind (`run-hks-test.sh --all`).

## Platform Architecture

| Layer | Implementation |
|---|---|
| Kubernetes | v1.35.7, kubeadm, 4 nodes (1 control-plane, 3 workers), containerd |
| CNI | Calico via Tigera Operator v1.40.8; NetworkPolicy enforced |
| Storage | Rook-managed Ceph (`HEALTH_OK`), `rook-ceph-block` StorageClass (RWO/RBD) |
| Ingress | Community ingress-nginx v1.12.1 (pre-existing) |
| Monitoring | kube-prometheus stack: Prometheus 3.10.0 (2 replicas), Alertmanager (3 replicas), Grafana, Prometheus Operator, `prometheus-adapter` serving `metrics.k8s.io` |
| Autoscaler | HPA functional via `prometheus-adapter`; no Cluster Autoscaler |

## Capability Results

See `HKS_CAPABILITY_MATRIX.md` for the full table. Headline: **26 of 28
tracked capabilities passed** live validation; 1 (Cluster Autoscaler) is
marked infrastructure-not-available; 1 (Gateway API) was intentionally left
unactivated as a cluster-scoped change requiring explicit opt-in (see
`NETWORKING_DECISION.md`).

## Networking

- **ClusterIP / Service DNS:** all standard forms (`svc`, `svc.ns`,
  `svc.ns.svc`, `svc.ns.svc.cluster.local`) resolved correctly from within
  pods.
- **NodePort:** answered from all 4 node IPs.
- **LoadBalancer:** API-level support confirmed (`Service.type=LoadBalancer`
  is accepted); no external IP is ever allocated because no MetalLB or cloud
  LB controller exists on this cluster. This is the same behavior already
  exhibited by the pre-existing ingress-nginx Service.
- **Ingress:** works correctly, with one operational nuance worth flagging —
  the pre-existing ingress-nginx Service uses `externalTrafficPolicy: Local`,
  so its NodePort only answers on the node currently running the controller
  pod. This is standard ingress-nginx behavior (preserves client source IP)
  but is easy to misdiagnose as a networking fault if undocumented.
- **TLS:** functional via the ingress controller's default self-signed
  certificate; no cluster-managed certificate issuance (e.g. cert-manager)
  was found or tested.
- **Private/public access:** every address on this cluster (node IPs,
  Service IPs, Pod IPs) is RFC1918-private. There is no publicly routable
  path from outside the host network today.
- **Gateway API:** not currently active, but latent — Calico's Tigera
  Operator can install and run it (Envoy-based data plane) via a single
  `GatewayAPI` custom resource. Given the community ingress-nginx project's
  retirement (March 2026), this is the recommended migration path when the
  platform team is ready to make that cluster-scoped change.

## Workload Management

- Deployments, rolling updates (`maxUnavailable:1`/`maxSurge:1`), and
  rollback (`kubectl rollout undo`, which correctly reused the prior
  ReplicaSet rather than recreating it) all worked exactly as expected.
- Scheduling constraints — resource requests/limits, `nodeSelector`,
  required node affinity, taints/tolerations — all enforced correctly.
- Soft pod anti-affinity and topology spread constraints *influenced but did
  not guarantee* perfectly even pod distribution under node contention; this
  is expected behavior for `preferred`/`ScheduleAnyway` constraints, not a
  defect, but worth knowing before assuming "3 replicas = 1 per node" holds
  under load from other workloads.

## Autoscaling

- **HPA:** PASS. 2→6 replicas in ~40 seconds under synthetic CPU load
  driven through the app's own load generator; clean scale-down to
  `minReplicas` once load stopped and the stabilization window elapsed.
- **Cluster Autoscaler:** NOT AVAILABLE on this instance. A controlled
  resource-exhaustion test (10 pods × 1200m CPU against ~3.5 CPU of free
  cluster capacity) left 7 pods `Pending` for the full observation window
  with zero autoscaler reaction and no change in node count — expected,
  given no autoscaler workload or node-pool integration exists here.

## Storage

- CSI drivers for both RBD (block, RWO) and CephFS (file, RWX) are
  registered, but only a `rook-ceph-block` StorageClass exists — RWX is not
  configured on this cluster today.
- A marker value written to an RBD-backed PVC survived pod deletion and
  recreation on a **different** pod instance, confirming the volume (not
  the node's local disk) is the source of truth.
- Rook/Ceph itself reports `HEALTH_OK` (3 mons, 2 mgrs, 3 OSDs) and was not
  modified by any part of this test suite.

## Observability

- The existing Prometheus/Grafana/Alertmanager stack was not modified.
- ServiceMonitor-based scrape discovery required a namespace-scoped RBAC
  grant that this suite added (documented, additive, reversible) — see
  "gaps" above.
- Application metrics (`http_requests_total`, `http_request_duration_seconds`,
  `app_cpu_work_seconds_total`, `app_requests_in_flight`, `app_info`) are
  live in Prometheus and queryable today.

## Advanced Deployment

- **Blue/Green:** two independent Deployments behind one Service; traffic
  cutover and rollback both instantaneous (Service-selector patch); both
  color tracks coexisted without interference.
- **Canary:** ingress-nginx's native `canary-weight` annotation delivered a
  45/5 (90/10 target) split over 50 requests with no service mesh installed.

## Security

- The sample app runs under its own ServiceAccount with a least-privilege
  namespaced Role (`get/list/watch` on `pods`/`configmaps`/`services`
  only), `automountServiceAccountToken: false`.
- NetworkPolicy (Calico) enforcement was proven in both directions:
  explicitly allowed traffic passed, explicitly denied traffic was dropped
  (connection timeout, not a rejection — consistent with default-deny
  behavior).

## Gaps

- Cluster Autoscaler: infrastructure integration absent on this instance
  (see Autoscaling above).
- Gateway API: CRDs not installed; latent capability via Calico's Tigera
  Operator, intentionally left as an opt-in follow-up (cluster-scoped
  change).
- RWX (CephFS) storage: CSI driver present, no StorageClass configured;
  multi-writer volume access was not exercised.
- PodMonitor: CRD present, not exercised (ServiceMonitor covered the same
  need for this app).
- TLS via a managed CA (e.g. cert-manager): not present, not tested — only
  the ingress controller's default self-signed certificate was exercised.
- No public network path exists anywhere on this cluster; all
  public/private-access testing was necessarily private-only.

## Recommendations

**What HKS should provide by default:**
- A documented, one-command way to extend Prometheus's namespace-scoped
  RBAC to a new application namespace (or reconsider whether a cluster-wide
  read grant is an acceptable tradeoff for this platform's threat model) —
  today it's a silent gap that produces zero scrape targets with no error
  visible to the application team.
- Clear guidance alongside any pre-installed ingress-nginx that it is the
  retired community project, plus a documented migration path to the
  Gateway API option Calico already supports out of the box.

**What administrators should expect to configure per-cluster:**
- Cluster Autoscaler infrastructure integration, if node-level elastic
  scaling is required — this is inherently deployment-specific (cloud
  provider, node-pool controller, or bare-metal equivalent) and won't be
  present on static/on-prem node sets by default.
- A CephFS (or equivalent RWX) StorageClass, if workloads need shared
  multi-writer volumes — block/RWO is available by default, RWX is not.
- A managed TLS certificate flow (e.g. cert-manager) if anything beyond the
  ingress controller's self-signed default certificate is required.

## Overall HKS Readiness Score

Based only on capabilities actually validated in this session:

**26 / 28 tracked capabilities PASSED** live validation on this cluster.
Of the 2 remaining: 1 is an infrastructure gap specific to this instance
(Cluster Autoscaler), and 1 is a deliberately-deferred opt-in enhancement
(Gateway API). No capability tested here returned a genuine FAIL.

This cluster is **ready for general application workloads** exercising
standard Kubernetes primitives (deployments, scaling, storage, networking,
observability, progressive delivery). Node-level elastic scaling and
shared/multi-writer storage require additional platform-level setup before
they can be relied upon, and should be scoped explicitly with any team that
needs them.
