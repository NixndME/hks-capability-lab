# Test Results

Run date: 2026-08-12. Cluster: `kubernetes-admin@HKS` (kubeadm, 4 nodes,
v1.35.7). Full raw evidence under `evidence/`.

---

### NET-001 — Port-forward access
**Purpose:** confirm the most basic access path works.
**Prerequisites:** app deployed.
**Commands:** `kubectl -n hks-capability-lab port-forward svc/hks-lab-app 18080:80`
**Expected:** HTTP 200 on `http://localhost:18080/`
**Actual:** HTTP 200, `/api/info` returned valid JSON.
**Result:** PASS
**Evidence:** `evidence/access-modes/portforward.txt`

### NET-002 — ClusterIP / in-cluster Service DNS
**Purpose:** validate service discovery DNS forms.
**Commands:** exec into a pod, resolve `hks-lab-app`, `hks-lab-app.hks-capability-lab`, `hks-lab-app.hks-capability-lab.svc`, `hks-lab-app.hks-capability-lab.svc.cluster.local`.
**Expected:** all 4 forms resolve and return HTTP 200.
**Actual:** all 4 returned HTTP 200.
**Result:** PASS

### NET-003 — NodePort
**Purpose:** confirm NodePort answers from every node, not just the one running a pod.
**Commands:** `curl http://<node-ip>:<nodeport>/` for all 4 node IPs.
**Expected:** HTTP 200 from all reachable nodes.
**Actual:** HTTP 200 from all 4 node IPs (`externalTrafficPolicy: Cluster`, the default).
**Result:** PASS
**Limitations:** node IPs are RFC1918 private (192.168.122.0/24) — no public path.

### NET-004 — LoadBalancer
**Purpose:** distinguish API support from infrastructure availability.
**Commands:** `kubectl expose deployment hks-lab-app --type=LoadBalancer` (temporary).
**Expected/Actual:** Service accepted, `EXTERNAL-IP` stayed `<pending>` indefinitely — identical behavior to the pre-existing `ingress-nginx-controller` LoadBalancer Service.
**Result:** LOADBALANCER = API SUPPORTED / INFRASTRUCTURE = NOT AVAILABLE. Not a defect — no MetalLB or cloud LB controller exists on this cluster.
**Cleanup:** temporary Service deleted immediately after evidence capture.

### NET-005 — Ingress
**Purpose:** validate Ingress routing + discover any surprises.
**Commands:** `curl -H "Host: hks-demo.lab.local" http://<node-ip>:<http-nodeport>/`
**Expected:** HTTP 200 from the Ingress-routed backend.
**Actual:** Initial attempt against 2 of 4 node IPs **timed out**. Root cause:
`ingress-nginx-controller` Service has `externalTrafficPolicy: Local`
(standard ingress-nginx default, preserves client source IP) — NodePort only
answers on the node actually running the controller pod. Retested against
that node: HTTP 200, correct backend response. Also validated HTTPS via the
controller's default self-signed cert (NodePort 30337): HTTP 200.
**Result:** PASS (with the `externalTrafficPolicy` behavior documented as
expected, not a bug).
**Evidence:** `evidence/access-modes/ingress.txt`

---

### STG-001 — Storage: PVC provisioning
**Commands:** apply `manifests/storage-test.yaml`.
**Expected:** PVC reaches `Bound`.
**Actual:** Bound immediately to a dynamically-provisioned `rook-ceph-block` RBD volume.
**Result:** PASS

### STG-002 — Storage: persistence across pod restart
**Commands:** write `HKS_STORAGE_TEST=<timestamp>` to `/data/marker.txt`, delete the pod, wait for replacement, read the file back.
**Expected:** identical content on the new pod.
**Actual:** identical content, new pod name confirmed different from the original.
**Result:** PASS
**Full writeup:** `STORAGE_VALIDATION.md`

---

### MON-001 — Prometheus Operator CRD acceptance
**Commands:** apply ServiceMonitor + PrometheusRule from `hks-capability-lab.yaml` / `manifests/monitoring.yaml`.
**Actual:** both objects accepted.
**Result:** PASS

### MON-002 — Prometheus scrape target health
**Expected:** app pods appear as `up` targets in Prometheus.
**Actual (first attempt):** zero targets — `prometheus-k8s`'s ServiceAccount lacked RBAC to list Services/Endpoints/Pods in the new namespace (this cluster scopes Prometheus RBAC per-namespace, pre-authorized only for `default`/`kube-system`/`monitoring`). **Fixed** by adding a namespace-scoped Role/RoleBinding mirroring the platform's own pattern (now part of `hks-capability-lab.yaml`, fully additive). Also found and fixed a double-scrape (ServiceMonitor selector originally matched both the ClusterIP and NodePort Service).
**Actual (after fix):** exactly 2 targets (1 per pod), both `up`; `app_info`, `http_requests_total`, `http_request_duration_seconds_*` all queryable.
**Result:** PASS (capability exists; missing prerequisite identified and resolved)
**Full writeup:** `PROMETHEUS_VALIDATION.md`

---

### AUT-001 — HPA scale-up
**Commands:** `/api/load?cpu=90&duration=240&concurrency=2` on all running pods.
**Expected:** replica count increases as CPU utilization exceeds the 50% target.
**Actual:** 2 → 6 replicas (max) within ~40 seconds, CPU utilization peaked at 570% of target.
**Result:** PASS

### AUT-002 — HPA scale-down
**Expected:** replicas return to `minReplicas` after load stops and the stabilization window elapses.
**Actual:** 6 → 2 replicas roughly 60–90s after CPU utilization returned to 0%.
**Result:** PASS
**Full timeline:** `evidence/autoscaler/hpa-timeline.txt`

### AUT-003 — Cluster Autoscaler reaction
**Commands:** temporary 10-replica Deployment, 1200m CPU request each.
**Expected (if CA were present):** Pending pods trigger a new node, which joins and absorbs them.
**Actual:** 7/10 pods stuck `Pending` (`Insufficient cpu`) for the full ~2-minute observation window; node count stayed at 4 throughout; no autoscaler pod or event appeared at any point.
**Result:** NOT AVAILABLE — infrastructure integration absent on this (static KVM-VM) cluster, not a Kubernetes-level defect. Cleaned up immediately.
**Full writeup:** `AUTOSCALER_VALIDATION.md`

---

### DEP-001 — Rolling update v1 → v2
**Commands:** `kubectl set env deployment/hks-lab-app APP_VERSION=v2`
**Actual:** rolled out respecting `maxUnavailable:1/maxSurge:1`; `/api/info` on new pods reported `v2`.
**Result:** PASS

### DEP-002 — Rolling update v2 → v3
**Actual:** same as above, `/api/info` reported `v3`.
**Result:** PASS

### DEP-003 — Rollback v3 → v2
**Commands:** `kubectl rollout undo deployment/hks-lab-app`
**Actual:** reused the existing v2 ReplicaSet (`hks-lab-app-7cd694d464`) rather than recreating it; `/api/info` confirmed `v2` after pods settled.
**Result:** PASS

---

### Blue/Green
**Commands:** `manifests/blue-green.yaml` (2 independent Deployments), Service selector patched between `track: blue` and `track: green`.
**Actual:** 5/5 requests to blue returned `blue v1`; after the flip, 5/5 returned `green v2`; after rolling back, 5/5 returned `blue v1` again. Both tracks ran simultaneously throughout (2 blue + 2 green pods).
**Result:** PASS

### Canary
**Commands:** `manifests/canary.yaml`, `nginx.ingress.kubernetes.io/canary-weight: "10"`.
**Actual:** 50 requests via the Ingress → 45 stable (v2) / 5 canary (v3) — a 90/10 split matching the configured weight.
**Result:** PASS. Native ingress-nginx canary annotations were sufficient; no service mesh required.

### NetworkPolicy
**Commands:** `manifests/network-policy.yaml` — default-deny on backend pods + explicit allow from frontend-labeled pods, using Calico.
**Actual:** `frontend → backend` = HTTP 200 (allowed). `untrusted → backend` = connection timeout, curl exit 28 (denied).
**Result:** PASS, both directions proven.

### Scheduling
See `SCHEDULING_VALIDATION.md` for the full breakdown (5 sub-tests: soft
anti-affinity/topology spread, `nodeSelector`, required node affinity,
taints/tolerations, resource-request-driven scheduling). All PASS except a
noted caveat that *soft* anti-affinity/topology-spread constraints do not
guarantee perfectly even distribution under node contention (expected
behavior, documented, not a defect).

### Resiliency
- **Readiness failure:** pod correctly removed from Service endpoints while
  unready (`READY 0/1`), and rejoined automatically once the injected
  failure window expired. PASS.
- **Liveness failure:** container restarted after 3 consecutive probe
  failures (`RESTARTS` incremented, `kubectl describe pod` showed the
  `Unhealthy` → `Killing` → `Created`/`Started` event sequence). PASS.
- **Explicit crash (`os._exit(1)`):** container restarted automatically.
  PASS.
- **Pod deletion under load:** Service remained reachable throughout
  replacement; desired replica count (2) was restored within ~10s. PASS.

**Full evidence:** `evidence/resiliency/resiliency.txt`

---

## Summary

| Category | Pass | Not Available (infra gap) | Not Validated |
|---|---|---|---|
| Networking | 5/5 | 1 (LoadBalancer, documented) | 0 |
| Storage | 2/2 | 0 | RWX (CephFS) not configured |
| Monitoring | 2/2 | 0 | PodMonitor not exercised |
| Autoscaling | 2/2 (HPA) | 1 (Cluster Autoscaler) | 0 |
| Deployments | 3/3 | 0 | 0 |
| Advanced deployment | 2/2 (blue/green, canary) | 0 | 0 |
| NetworkPolicy | 1/1 | 0 | 0 |
| Scheduling | 5/5 (1 with caveat) | 0 | 0 |
| Resiliency | 4/4 | 0 | 0 |
