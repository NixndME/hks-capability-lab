# Scheduling Validation

All tests use disposable pods labeled `hks-capability-lab/role: sched-test`
in the `hks-capability-lab` namespace, cleaned up immediately after each
check. Full evidence: `evidence/scheduling/scheduling.txt`.

## 1. Pod anti-affinity + topology spread constraints (main app)

`hks-lab-app`'s pod template carries a `preferredDuringSchedulingIgnoredDuringExecution`
pod anti-affinity (weight 100, `topologyKey: kubernetes.io/hostname`) and a
`topologySpreadConstraint` (`maxSkew: 1`, `whenUnsatisfiable: ScheduleAnyway`)
on the same key — both **soft** constraints.

Scaled to 3 replicas:

```
hks-lab-app-7cd694d464-6gqnr   hks-worker-3
hks-lab-app-7cd694d464-gstjd   hks-worker-1
hks-lab-app-7cd694d464-nq9h5   hks-worker-3
```

**Result: 2 nodes used out of 3 available**, not a perfect 1-per-node spread.
This is expected and correct given the constraints used are `preferred`
(soft), not `required` — at the time of scheduling, `hks-worker-2` was
already running 5 other test pods (blue/green/canary deployments from tasks
running earlier in the same session), so the scheduler's overall scoring
favored packing rather than perfect topology spread. This is a useful,
honest data point: **soft anti-affinity influences but does not guarantee
even distribution under contention.** An earlier, uncontended run of the
same Deployment (see `00-cluster-discovery.md` / initial deploy evidence)
did land exactly 1 pod per node across all 3 workers.

## 2. `nodeSelector`

Pod with `nodeSelector: {ceph-storage: "enabled"}` (a label present on all 3
workers, not on the control-plane node):

```
sched-test-nodeselector   hks-worker-3
```

**PASS** — landed on a labeled worker, confirming label-based exclusion of
the control-plane node works as expected.

## 3. Required node affinity (pin to an exact node)

Pod with `requiredDuringSchedulingIgnoredDuringExecution` node affinity on
`kubernetes.io/hostname In [hks-worker-2]`:

```
sched-test-affinity   hks-worker-2
```

**PASS** — landed on exactly the requested node.

## 4. Taints/tolerations

**Without** a toleration for the control-plane's
`node-role.kubernetes.io/control-plane:NoSchedule` taint, a pod
`nodeSelector`'d to `hks-master` stayed `Pending`:

```
0/4 nodes are available: 1 node(s) had untolerated taint(s),
3 node(s) didn't match Pod's node affinity/selector.
```

**With** an explicit toleration for that taint, the same pod scheduled
successfully:

```
sched-test-with-toleration   hks-master
```

**PASS** — the control-plane taint is enforced and a matching toleration
correctly overrides it. (This only ran a `sleep`-only pod for a few seconds
and was deleted immediately; no control-plane configuration was touched.)

## 5. Resource requests/limits driving scheduling decisions

Covered in depth in `AUTOSCALER_VALIDATION.md` §2: 10 pods requesting 1200m
CPU each against ~1.1–1.4 CPU/node of free capacity produced
`FailedScheduling` / `Insufficient cpu` for 7 of them, proving resource
requests are enforced as real scheduling constraints, not just accounting.

## Summary

| Mechanism | Result |
|---|---|
| Pod anti-affinity (preferred) | Working, but soft — doesn't guarantee even spread under contention |
| Topology spread constraint (ScheduleAnyway) | Same caveat as above (soft) |
| `nodeSelector` | PASS |
| Required node affinity | PASS |
| Taints (control-plane) | Enforced |
| Tolerations | Correctly override matching taints |
| Resource requests as scheduling gate | PASS (`Insufficient cpu`) |
