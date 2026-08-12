#!/usr/bin/env bash
# Storage validation: apply manifests/storage-test.yaml, write a known
# marker, delete the pod, confirm the marker survives on the new pod.
# See STORAGE_VALIDATION.md for the reasoning and a worked example.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/lib.sh
require_config
resolve_auto_config

NS="$NAMESPACE"

log_step "STG-001: Deploy isolated PVC + pod"
render_apply manifests/storage-test.yaml
if ! wait_rollout "$NS" hks-lab-storage-test 90s; then
  log_fail "STG-001 storage-test deployment did not become ready"
  exit 1
fi
PVC_STATUS=$(kubectl -n "$NS" get pvc hks-lab-storage-test -o jsonpath='{.status.phase}')
if [[ "$PVC_STATUS" == "Bound" ]]; then
  log_pass "STG-001 PVC bound ($STORAGE_CLASS)"
else
  log_fail "STG-001 PVC status: $PVC_STATUS"
  exit 1
fi

log_step "STG-002: Write + verify marker, delete pod, verify persistence"
POD1=$(kubectl -n "$NS" get pods -l hks-capability-lab/role=storage-test -o jsonpath='{.items[0].metadata.name}')
MARKER="HKS_STORAGE_TEST=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
kubectl -n "$NS" exec "$POD1" -- sh -c "echo '$MARKER' > /data/marker.txt"
READBACK1=$(kubectl -n "$NS" exec "$POD1" -- cat /data/marker.txt)
[[ "$READBACK1" == "$MARKER" ]] || { log_fail "STG-002 marker mismatch immediately after write"; exit 1; }

kubectl -n "$NS" delete pod "$POD1" >/dev/null
wait_rollout "$NS" hks-lab-storage-test 90s >/dev/null
POD2=$(kubectl -n "$NS" get pods -l hks-capability-lab/role=storage-test -o jsonpath='{.items[0].metadata.name}')
READBACK2=$(kubectl -n "$NS" exec "$POD2" -- cat /data/marker.txt)

if [[ "$READBACK2" == "$MARKER" && "$POD1" != "$POD2" ]]; then
  log_pass "STG-002 data persisted across pod restart ($POD1 -> $POD2): $READBACK2"
else
  log_fail "STG-002 persistence check failed (wrote: $MARKER, read: $READBACK2)"
fi
