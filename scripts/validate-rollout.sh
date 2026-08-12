#!/usr/bin/env bash
# Rolling update v1 -> v2 -> v3 (via APP_VERSION env change, which triggers
# a normal Deployment rolling update), then rollback. See TEST_RESULTS.md
# (DEP-* test IDs) for a worked example from this cluster.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/lib.sh
require_config

NS="$NAMESPACE"

current_version() {
  local pod
  pod=$(kubectl -n "$NS" get pods -l app.kubernetes.io/name=hks-lab-app,hks-capability-lab/track=stable --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
  kubectl -n "$NS" exec "$pod" -- python3 -c "
import urllib.request, json
print(json.load(urllib.request.urlopen('http://localhost:8080/api/info'))['version'])
"
}

log_step "DEP-001: v1 -> v2 rolling update"
kubectl -n "$NS" set env deployment/hks-lab-app APP_VERSION=v2
if wait_rollout "$NS" hks-lab-app 90s; then
  V=$(current_version)
  [[ "$V" == "v2" ]] && log_pass "DEP-001 rolled out to v2" || log_fail "DEP-001 rollout finished but app reports version=$V"
else
  log_fail "DEP-001 rollout did not complete"
fi

log_step "DEP-002: v2 -> v3 rolling update"
kubectl -n "$NS" set env deployment/hks-lab-app APP_VERSION=v3
if wait_rollout "$NS" hks-lab-app 90s; then
  V=$(current_version)
  [[ "$V" == "v3" ]] && log_pass "DEP-002 rolled out to v3" || log_fail "DEP-002 rollout finished but app reports version=$V"
else
  log_fail "DEP-002 rollout did not complete"
fi

log_step "DEP-003: rollback v3 -> v2"
kubectl -n "$NS" rollout undo deployment/hks-lab-app
if wait_rollout "$NS" hks-lab-app 90s; then
  sleep 3
  V=$(current_version)
  [[ "$V" == "v2" ]] && log_pass "DEP-003 rolled back to v2" || log_fail "DEP-003 rollback finished but app reports version=$V"
else
  log_fail "DEP-003 rollback did not complete"
fi

kubectl -n "$NS" rollout history deployment/hks-lab-app | tee -a "$RESULTS_LOG"
