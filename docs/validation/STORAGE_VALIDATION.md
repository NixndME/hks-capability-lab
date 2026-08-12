# Storage Validation

## What was tested

An isolated PVC + single-replica Deployment (`manifests/storage-test.yaml`)
in the `hks-capability-lab` namespace, using the cluster's only existing
StorageClass. Rook/Ceph itself was not modified — this only consumes it as
any application would.

## Environment

| Item | Value |
|---|---|
| StorageClass | `rook-ceph-block` |
| Provisioner | `rook-ceph.rbd.csi.ceph.com` |
| Access mode | `ReadWriteOnce` |
| Volume binding mode | `Immediate` |
| Reclaim policy | `Delete` |
| Backing system | Rook-managed Ceph cluster `rook-ceph` (namespace `rook-ceph`), `HEALTH_OK`, 3 mons / 2 mgrs / 3 OSDs |
| Deployment strategy | `Recreate` (required for RWO volumes so the old pod fully detaches before the new one attaches) |

## Steps executed

1. Applied `manifests/storage-test.yaml` → PVC `hks-lab-storage-test` bound
   immediately (`Bound`, 1Gi, `rook-ceph-block`) to a dynamically-provisioned
   RBD volume (`pvc-b8b96726-3d7a-4fe2-94e8-6fda5b09d329`).
2. `kubectl exec` into the running pod
   (`hks-lab-storage-test-7b87d9467b-8k28r`) and wrote a known marker:
   `HKS_STORAGE_TEST=2026-08-12T11:45:44Z` to `/data/marker.txt`.
3. Read the file back in the same pod — confirmed identical content.
4. `kubectl delete pod` on that pod. The Deployment (strategy `Recreate`)
   waited for full termination, detached the RBD volume, then created a
   **new** pod (`hks-lab-storage-test-7b87d9467b-6nvxd`) and reattached the
   same PVC.
5. `kubectl exec` into the new pod and read `/data/marker.txt`.

## Result

```
Written:  HKS_STORAGE_TEST=2026-08-12T11:45:44Z
Read back (new pod, same PVC): HKS_STORAGE_TEST=2026-08-12T11:45:44Z
```

**PASS** — data survived pod deletion/recreation on a different pod
instance backed by the same PVC.

## Scope / limitations

- Only **RWO (block/RBD)** was validated. The cluster's `rook-ceph.cephfs.csi.ceph.com`
  CSI driver is registered but no `CephFilesystem` exists yet, so there is no
  RWX StorageClass to test multi-writer access with today. This is a gap in
  the *cluster's current configuration*, not in Rook/Ceph's capability —
  creating a CephFilesystem would enable it, but doing so is a Rook/Ceph
  cluster-scoped change and was intentionally not made (see safety rules).
- The pod was rescheduled onto storage already local-reachable to any of the
  3 ceph-storage-enabled workers — RBD volumes are not node-pinned in this
  cluster (any of the 3 OSD-hosting workers can serve it), so this also
  implicitly confirms the volume is not tied to the node the first pod
  happened to land on.
- Full evidence: `evidence/storage-test.txt`.
