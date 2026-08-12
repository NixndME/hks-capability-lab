# Autoscaler Validation

Two distinct capabilities, tested separately per the platform-vs-test-failure
distinction:

1. **Horizontal Pod Autoscaler (HPA)** — pod-level scaling within existing
   node capacity. Kubernetes-native, backed by `prometheus-adapter`'s
   `metrics.k8s.io` implementation on this cluster.
2. **Cluster Autoscaler (CA)** — node-level scaling (adding VMs when pods
   can't be scheduled). Requires an infrastructure integration beneath
   Kubernetes; **not present on this cluster** (see `00-cluster-discovery.md`
   §7).

## 1. HPA — PASS, fully validated end-to-end

**Setup:** `hks-lab-app` HPA (`autoscaling/v2`), `minReplicas: 2`,
`maxReplicas: 6`, target 50% average CPU utilization of the 100m request.

**Method:** used the app's own `/api/load` endpoint (no external tooling)
to drive each running pod to ~90% CPU for 240 seconds, then watched
`kubectl get hpa`/`get pods` every 20s until the load expired and the
deployment settled back down.

**Timeline** (full log: `evidence/autoscaler/hpa-timeline.txt`):

| Time (UTC) | CPU vs target | Replicas | Note |
|---|---|---|---|
| 11:57:43 | 0%/50% | 2 | idle baseline (HPA had already scaled 3→2 on its own before load started) |
| 12:01:05 | 356%/50% | 2→6 (scaling) | load kicks in, 4 new pods created within ~20s |
| 12:01:25 | 356%/50% | 6 | at `maxReplicas` |
| 12:02:06 | 472%/50% | 6 | sustained under load |
| 12:04:46 | 532%/50% | 6 | load still running |
| 12:05:06 | 117%/50% | 6 | load duration (240s) expiring |
| 12:05:46 | 0%/50% | 6 | idle, stabilization window running |
| 12:06:47 | 0%/50% | **2** | scaled back down to `minReplicas` |

**Result: PASS.** Scale-up 2→6 took ~40 seconds once the metric crossed
threshold; scale-down 6→2 happened cleanly once CPU stayed at 0% past the
60s `stabilizationWindowSeconds`. No manual intervention required at any
point.

## 2. Cluster Autoscaler — NOT AVAILABLE (infrastructure gap, not a platform defect)

**Discovery:** no `cluster-autoscaler` Pod/Deployment exists anywhere in the
cluster (`kubectl get pods -A`), and there is no node-pool/node-group CRD or
cloud-controller-manager integration. This is a static 4-node kubeadm
cluster on local KVM/libvirt VMs (see `00-cluster-discovery.md`).

**Test performed anyway, to produce real evidence rather than assume:**
deployed a temporary, clearly-labeled Deployment
(`hks-lab-ca-exhaustion-test`, 10 replicas × 1200m CPU request each — large
enough to exceed the ~1.1–1.4 CPU/node actually free at the time across the
3 schedulable workers).

**Result:**

```
0/4 nodes are available: 1 node(s) had untolerated taint(s), 3 Insufficient cpu.
```

- 3 of 10 pods scheduled (onto free capacity on the 3 workers).
- **7 pods stayed `Pending`** with `FailedScheduling` / `Insufficient cpu`
  for the full observation window (~2 minutes).
- Node count stayed at **4** throughout — no new node was provisioned.
- No `cluster-autoscaler`-related pod or event appeared at any point.
- Cleaned up immediately after capturing evidence
  (`kubectl delete deployment hks-lab-ca-exhaustion-test`) — this was a
  temporary resource, not part of the reusable manifest set.

Full evidence: `evidence/autoscaler/ca-exhaustion.txt`.

## Conclusion — platform capability vs. this instance

```
Pending workload observed:        YES
Autoscaler reaction observed:     NO
New node added:                   NO
Node became Ready:                N/A
Previously unschedulable pods
  eventually scheduled:           NO (remained Pending until cleanup)
```

Per the required distinction:

```
Cluster Autoscaler = Kubernetes-side mechanism (node pool scale requests)
Infrastructure integration for HKS's Cluster Autoscaler = NOT PRESENT on this cluster
Therefore:
CLUSTER AUTOSCALER = NOT VALIDATED on this instance (infra not available)
HPA (pod-level autoscaling)   = VALIDATED, PASS
```

HKS documentation states Cluster Autoscaler is supported by the platform;
this specific lab cluster (a static, self-hosted set of KVM VMs) simply
doesn't have that integration wired up. Re-running this same test
(`run-hks-test.sh --all` or menu option 5) against an HKS cluster with an
actual node-pool/cloud integration would be expected to show scale-up
following the same Pending-pod trigger observed here.
