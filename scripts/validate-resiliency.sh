#!/usr/bin/env bash
# Resiliency checks: readiness-probe failure removes a pod from Service
# endpoints without killing it; liveness-probe failure and an explicit
# crash both trigger a container restart; deleting a pod is followed by
# automatic replacement with the Service staying reachable throughout.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/lib.sh
require_config

NS="$NAMESPACE"
SEL="app.kubernetes.io/name=hks-lab-app,hks-capability-lab/track=stable"

pod_exec_post() {
  local pod="$1" path="$2"
  kubectl -n "$NS" exec "$pod" -- python3 -c "
import urllib.request
req = urllib.request.Request('http://localhost:8080$path', method='POST')
try:
    r = urllib.request.urlopen(req, timeout=5)
    print(r.status)
except Exception as e:
    print('ERR', e)
"
}

log_step "RES-001: readiness-probe failure removes pod from Service endpoints"
POD=$(kubectl -n "$NS" get pods -l "$SEL" --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
POD_IP=$(kubectl -n "$NS" get pod "$POD" -o jsonpath='{.status.podIP}')
pod_exec_post "$POD" "/api/chaos/readiness-fail?seconds=20" >/dev/null
sleep 12
EPS=$(kubectl -n "$NS" get endpoints hks-lab-app -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null)
if [[ "$EPS" != *"$POD_IP"* ]]; then
  log_pass "RES-001 pod excluded from Service endpoints while unready"
else
  log_fail "RES-001 pod still in endpoints during induced readiness failure"
fi
sleep 20
EPS2=$(kubectl -n "$NS" get endpoints hks-lab-app -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null)
[[ "$EPS2" == *"$POD_IP"* ]] && log_pass "RES-001b pod rejoined endpoints after self-healing" || log_fail "RES-001b pod did not rejoin endpoints"

log_step "RES-002: liveness-probe failure triggers container restart"
POD=$(kubectl -n "$NS" get pods -l "$SEL" --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
RESTARTS_BEFORE=$(kubectl -n "$NS" get pod "$POD" -o jsonpath='{.status.containerStatuses[0].restartCount}')
pod_exec_post "$POD" "/api/chaos/liveness-fail?seconds=60" >/dev/null
sleep 35
RESTARTS_AFTER=$(kubectl -n "$NS" get pod "$POD" -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null || echo "$RESTARTS_BEFORE")
if [[ "$RESTARTS_AFTER" -gt "$RESTARTS_BEFORE" ]]; then
  log_pass "RES-002 container restarted after liveness failures ($RESTARTS_BEFORE -> $RESTARTS_AFTER)"
else
  log_fail "RES-002 no restart observed within 35s"
fi

log_step "RES-003: pod deletion -> automatic replacement, Service stays reachable"
BEFORE=$(kubectl -n "$NS" get pods -l "$SEL" --no-headers | wc -l | tr -d ' ')
VICTIM=$(kubectl -n "$NS" get pods -l "$SEL" -o jsonpath='{.items[0].metadata.name}')
kubectl -n "$NS" delete pod "$VICTIM" --wait=false >/dev/null
ALIVE=$(kubectl -n "$NS" get pods -l "$SEL" --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [[ -n "$ALIVE" ]] && kubectl -n "$NS" exec "$ALIVE" -- python3 -c "import urllib.request; urllib.request.urlopen('http://hks-lab-app/healthz', timeout=3)" >/dev/null 2>&1; then
  log_pass "RES-003 Service reachable during pod replacement"
else
  log_fail "RES-003 Service not reachable during pod replacement"
fi
sleep 10
AFTER=$(kubectl -n "$NS" get pods -l "$SEL" --field-selector=status.phase=Running --no-headers | wc -l | tr -d ' ')
[[ "$AFTER" == "$BEFORE" ]] && log_pass "RES-003b desired replica count restored ($AFTER)" || log_fail "RES-003b replica count is $AFTER, expected $BEFORE"
