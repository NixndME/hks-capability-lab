#!/usr/bin/env bash
# Verifies the app's ServiceMonitor is actually being scraped by the
# cluster's existing Prometheus (not just that the CRD was accepted).
# See docs/validation/PROMETHEUS_VALIDATION.md for the RBAC gap this had to work around.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/lib.sh
require_config
resolve_auto_config

if ! has_prometheus_operator; then
  log_skip "MON-001 Prometheus Operator CRDs not found on this cluster -- skipping"
  exit 0
fi

log_step "MON-001: Prometheus Operator + ServiceMonitor present"
kubectl -n "$NAMESPACE" get servicemonitor hks-lab-app >/dev/null 2>&1 \
  && log_pass "MON-001 ServiceMonitor exists" \
  || { log_fail "MON-001 ServiceMonitor missing -- apply hks-capability-lab.yaml first"; exit 1; }

if [[ "$PROMETHEUS_NAMESPACE" == "none" ]]; then
  log_skip "MON-002 no Prometheus instance found via 'kubectl get prometheus -A'"
  exit 0
fi

log_step "MON-002: scrape target health (via port-forward)"
kubectl -n "$PROMETHEUS_NAMESPACE" port-forward svc/prometheus-k8s 19090:9090 >/dev/null 2>&1 &
PF_PID=$!
trap 'kill $PF_PID 2>/dev/null' EXIT
sleep 3

OK=false
for attempt in 1 2 3 4 5 6; do
  RESULT=$(curl -s "http://localhost:19090/api/v1/query" --data-urlencode "query=up{namespace=\"$NAMESPACE\"}" 2>/dev/null)
  COUNT=$(echo "$RESULT" | python3 -c "import json,sys;print(len(json.load(sys.stdin).get('data',{}).get('result',[])))" 2>/dev/null || echo 0)
  if [[ "$COUNT" != "0" ]]; then
    HEALTHY=$(echo "$RESULT" | python3 -c "
import json,sys
d = json.load(sys.stdin)
vals = [r['value'][1] for r in d['data']['result']]
print(all(v=='1' for v in vals))
")
    if [[ "$HEALTHY" == "True" ]]; then
      log_pass "MON-002 $COUNT target(s) up for namespace=$NAMESPACE"
      OK=true
      break
    fi
  fi
  log_info "MON-002 attempt $attempt: not yet visible (Prometheus config reload can take up to ~90s after a ServiceMonitor change), retrying..."
  sleep 15
done
$OK || log_fail "MON-002 no healthy scrape target found after retries -- check RBAC (see docs/validation/PROMETHEUS_VALIDATION.md) and prometheus-operator logs"

kill $PF_PID 2>/dev/null
trap - EXIT
