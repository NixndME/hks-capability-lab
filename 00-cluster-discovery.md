# Cluster Discovery — HKS Kubernetes Capability Lab

Evidence collected: 2026-08-12, cluster context `kubernetes-admin@HKS`.
All commands below were executed live against the target cluster; raw output is
mirrored under `evidence/00-discovery/`.

## 1. Kubernetes core

| Item | Value |
|---|---|
| Client version (`kubectl`) | v1.36.3 |
| Server version | v1.35.7 |
| Node count | 4 (1 control-plane, 3 workers) |
| Container runtime | containerd://1.7.29 |
| OS | Ubuntu 24.04.4 LTS |
| Kernel | 6.8.0-136-generic |
| Arch | amd64 (all nodes) |

### Nodes

| Name | Roles | Internal IP | External IP | Taints | CPU cap/alloc | Mem cap/alloc |
|---|---|---|---|---|---|---|
| hks-master | control-plane | 192.168.122.230 | none | `node-role.kubernetes.io/control-plane:NoSchedule` | 2 / 2 | 4009872Ki / 3907472Ki |
| hks-worker-1 | \<none\> | 192.168.122.231 | none | none | 2 / 2 | 4009864Ki / 3907464Ki |
| hks-worker-2 | \<none\> | 192.168.122.232 | none | none | 2 / 2 | 4009864Ki / 3907464Ki |
| hks-worker-3 | \<none\> | 192.168.122.233 | none | none | 2 / 2 | 4009864Ki / 3907464Ki |

All 4 node IPs (192.168.122.0/24) are **RFC1918 private addresses** (libvirt/KVM
default NAT range). No node has an external/public IP. This is a self-hosted
HKS cluster running on local VMs, not a cloud-backed deployment.

All 3 workers carry the label `ceph-storage=enabled` (used by Rook/Ceph node
placement). No custom taints exist besides the standard control-plane taint,
so workloads schedule freely across the 3 workers by default.

### Existing namespaces

`calico-system, default, ingress-nginx, kube-node-lease, kube-public,
kube-system, logging, monitoring, rook-ceph, tigera-operator`

No pre-existing application namespace — the lab will create and use
`hks-capability-lab` exclusively for all test resources.

## 2. Networking / CNI

| Item | Value |
|---|---|
| CNI | **Calico**, installed via Tigera Operator |
| Tigera operator image | `quay.io/tigera/operator:v1.40.8` |
| Pod CIDR | `172.20.0.0/16` (Calico IPPool `default-ipv4-ippool`, VXLANCrossSubnet encap) |
| Service CIDR | `172.30.0.0/16` |
| DNS domain | `cluster.local` (CoreDNS, 2 replicas in `kube-system`) |
| kube-proxy | present as DaemonSet, mode unset → defaults to **iptables** |
| NetworkPolicy support | **Yes** — Calico enforces both native `networking.k8s.io/v1` NetworkPolicy and Calico's own CRD-based policies (`crd.projectcalico.org` — GlobalNetworkPolicy, Tiers, staged policies, etc.). One policy already exists: `calico-system/allow-apiserver`. |
| AdminNetworkPolicy CRDs | Present (`adminnetworkpolicies.policy.networking.k8s.io`) — Calico also supports the upstream Kubernetes Admin Network Policy API. |

**Evidence:** `kubectl get pods -A` shows `calico-node` (DaemonSet, 1/node),
`calico-typha`, `calico-kube-controllers`, `calico-apiserver`, and a
`calicoctl` debug pod, all in `calico-system`, all `Running`.

## 3. Ingress / Gateway

| Item | Value |
|---|---|
| IngressClass | `nginx`, controller `k8s.io/ingress-nginx` |
| Namespace | `ingress-nginx` |
| Controller image | `registry.k8s.io/ingress-nginx/controller:v1.12.1` — this **is** the community `kubernetes/ingress-nginx` project (not F5 NGINX Ingress Controller, not Kong/Traefik/HAProxy). |
| Service type | `LoadBalancer`, but `EXTERNAL-IP` is stuck at `<pending>` |
| NodePorts (fallback) | HTTP `31992/TCP`, HTTPS `30337/TCP` |
| Gateway API CRDs (`gateway.networking.k8s.io`) | **Not installed** — `kubectl get gatewayclass/gateway/httproute` all return "the server doesn't have a resource type" |
| Gateway API via Calico | **Available but not enabled.** The Tigera operator ships a `GatewayAPI` CRD (`gatewayapis.operator.tigera.io`) that, if a `GatewayAPI` custom resource is created, installs the standard Gateway API CRDs and an Envoy-based data plane. This is a **cluster-scoped change** (new CRDs, new controller) and was **not** enabled during discovery — see `NETWORKING_DECISION.md`. |
| Existing Ingress objects | None |

**Important context:** the community Ingress NGINX project was retired in
March 2026 (per project guidance). This cluster already has it installed and
running — it was not installed by this lab. It is being reused as-is for
Ingress-based tests; no second ingress controller is being installed. See
`NETWORKING_DECISION.md` for the full reasoning and the Gateway API
alternative.

## 4. LoadBalancer / external exposure

No MetalLB, no cloud-controller-manager, and no other `Service`
type=LoadBalancer implementation was found (`kubectl get pods -A` has no
metallb/speaker/controller pods, and the only LoadBalancer Service in the
cluster — `ingress-nginx-controller` — has sat at `EXTERNAL-IP: <pending>`
since creation).

Conclusion: `Service.type=LoadBalancer` is **API-supported** (Kubernetes
accepts the object) but **infrastructure-unavailable** (nothing ever
allocates an address). NodePort and port-forward are the only paths to
externally reach a Service on this cluster today.

## 5. Storage

| Item | Value |
|---|---|
| StorageClass | `rook-ceph-block` (provisioner `rook-ceph.rbd.csi.ceph.com`, reclaim `Delete`, binding `Immediate`, `allowVolumeExpansion: true`) |
| Default StorageClass | **None set** — no SC carries `storageclass.kubernetes.io/is-default-class`. PVCs must specify `storageClassName` explicitly. |
| CSI drivers | `rook-ceph.rbd.csi.ceph.com` (block/RWO), `rook-ceph.cephfs.csi.ceph.com` (registered, but no CephFS filesystem exists yet — no RWX StorageClass currently available), `csi.tigera.io` (Calico's ephemeral CSI, unrelated to app storage) |
| Rook/Ceph | **Present**, namespace `rook-ceph`, operator `rook/ceph:v1.19.3`. `CephCluster/rook-ceph` phase = `Ready`, health = `HEALTH_OK`, 3 mons, 2 mgrs (a/b), 3 OSDs (one per worker). |
| Existing PV/PVC | None |

Rook/Ceph is healthy and will **not** be modified. The lab will only consume
it through a new PVC against the existing `rook-ceph-block` StorageClass in
the isolated `hks-capability-lab` namespace. Only block storage (RWO) is
available out of the box — RWX (CephFS) is not configured, so multi-writer
volume tests are marked out of scope unless a CephFS filesystem is later
created (a cluster-scoped Rook change, not done here).

## 6. Observability — Prometheus

| Item | Value |
|---|---|
| Stack | kube-prometheus (Prometheus Operator) |
| Namespace | `monitoring` |
| Prometheus | `prometheus-k8s`, 2 replicas (StatefulSet-backed), version `3.10.0` |
| Alertmanager | `alertmanager-main`, 3 replicas |
| Grafana | `grafana/grafana:12.4.1`, 1 replica |
| kube-state-metrics, node-exporter, blackbox-exporter | all present |
| Prometheus Operator | Present (`prometheus-operator`), 2/2 |
| CRDs | `servicemonitors`, `podmonitors`, `probes`, `prometheusrules`, `alertmanagerconfigs`, `scrapeconfigs`, `thanosrulers` — full Operator CRD set is registered |
| Existing ServiceMonitors | 13, covering core cluster components (apiserver, coredns, kubelet, kube-state-metrics, node-exporter, etc.) |
| metrics.k8s.io (for `kubectl top` / HPA resource metrics) | Served by **`prometheus-adapter`** (2 replicas), registered as APIService `v1beta1.metrics.k8s.io`. `kubectl top nodes` works. **No separate `metrics-server` is installed** — HPA and `kubectl top` ride on the Prometheus stack. |
| Prometheus Service | ClusterIP `prometheus-k8s`, ports `9090` (UI/API), `8080` |

Nothing here will be modified. The lab will add a `ServiceMonitor` in its own
namespace pointing at the sample app (Prometheus Operator will auto-discover
it via its existing `serviceMonitorSelector`, which needs to be confirmed
empty/permissive — checked in `PROMETHEUS_VALIDATION.md`).

## 7. Autoscaling

| Item | Value |
|---|---|
| Cluster Autoscaler | **Not found.** No `cluster-autoscaler` Deployment/Pod anywhere in `kubectl get pods -A`, no node-group/node-pool CRDs, no cloud-provider integration. |
| HPA (Horizontal Pod Autoscaler) | Kubernetes API supports it (`autoscaling/v2` is a standard built-in API, not a CRD) and resource metrics are available via `prometheus-adapter`, so HPA is expected to be **functional** for CPU/memory-based scaling. Will be validated directly. |

This is a static 4-node kubeadm cluster on local KVM/libvirt VMs — there is no
infrastructure layer underneath Kubernetes that could add a 5th node on
demand. **Cluster Autoscaler capability is therefore "platform does not
support / infrastructure not available" on this particular HKS instance**,
not a test failure. HPA (pod-level scaling within the existing 4 nodes) is a
separate capability and will be tested end-to-end. See `AUTOSCALER_VALIDATION.md`.

## 8. RBAC / access

`kubectl auth can-i '*' '*' --all-namespaces` → `yes`. The kubeconfig in use
(`kubernetes-admin@HKS`) has cluster-admin. The lab will still create a
scoped ServiceAccount/Role/RoleBinding for the sample app itself (least
privilege for the workload, independent of the operator's own access level).

## 9. HKS/Morpheus-specific components

No Morpheus-specific controllers, CRDs, or agents were found in
`kubectl get crd` or `kubectl get pods -A` (no `morpheus-*` namespaces or
workloads). This appears to be a vanilla kubeadm cluster provisioned by HKS
without an in-cluster Morpheus agent, or that agent is out of scope of this
kubeconfig's visibility.

## Summary table

| Layer | Detected | Notes |
|---|---|---|
| CNI | Calico (Tigera Operator v1.40.8) | NetworkPolicy enforced |
| Ingress | community ingress-nginx v1.12.1 | pre-existing, retired upstream (Mar 2026), reused as-is |
| Gateway API | Not enabled | available via Tigera operator, cluster-scoped to enable |
| LoadBalancer | API only | no MetalLB/cloud LB — NodePort is the working external path |
| Storage | Rook-Ceph (HEALTH_OK) | `rook-ceph-block` RWO only, no default SC, no RWX |
| Monitoring | kube-prometheus stack | Prometheus 3.10.0, Operator present, ServiceMonitor/PodMonitor supported |
| Metrics API | prometheus-adapter | powers `kubectl top` and HPA |
| Cluster Autoscaler | Not present | static VM cluster, infra-level gap not a K8s gap |
| HPA | API + metrics available | expected functional, to be validated |
| RBAC | cluster-admin kubeconfig | scoped SA/Role created for the app anyway |
