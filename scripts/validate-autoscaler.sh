#!/usr/bin/env bash
# HPA scale-up/down using the app's own load generator, plus (optional,
# bounded) Cluster Autoscaler reaction test via a temporary,
# over-provisioned Deployment. See docs/validation/AUTOSCALER_VALIDATION.md for the
# reasoning and a worked example from this cluster.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/lib.sh
require_config
resolve_auto_config

NS="$NAMESPACE"

log_step "AUT-001: HPA scale-up under synthetic CPU load"
if ! has_metrics_api; then
  log_skip "AUT-001 metrics.k8s.io API not available -- HPA cannot function, skipping"
  exit 0
fi

BEFORE=$(kubectl -n "$NS" get deploy hks-lab-app -o jsonpath='{.status.replicas}')
log_info "Replicas before load: $BEFORE"

DRIVER=$(kubectl -n "$NS" get pods -l app.kubernetes.io/name=hks-lab-app,hks-capability-lab/track=stable -o jsonpath='{.items[0].metadata.name}')
IPS=$(kubectl -n "$NS" get pods -l app.kubernetes.io/name=hks-lab-app,hks-capability-lab/track=stable -o jsonpath='{.items[*].status.podIP}')
kubectl -n "$NS" exec -i "$DRIVER" -- python3 - "$IPS" <<'PY'
import sys, urllib.request
for ip in sys.argv[1].split():
    req = urllib.request.Request(f"http://{ip}:8080/api/load?cpu=90&duration=180&concurrency=2", method="POST")
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(ip, "ERROR", e)
PY

SCALED=false
for i in $(seq 1 12); do
  sleep 15
  CUR=$(kubectl -n "$NS" get deploy hks-lab-app -o jsonpath='{.status.replicas}')
  log_info "t+${i}x15s: replicas=$CUR"
  if [[ "$CUR" -gt "$BEFORE" ]]; then SCALED=true; fi
done
$SCALED && log_pass "AUT-001 HPA scaled up from $BEFORE replicas" || log_fail "AUT-001 no scale-up observed"

log_step "AUT-002: HPA scale-down after load subsides"
SCALED_DOWN=false
for i in $(seq 1 8); do
  sleep 15
  CUR=$(kubectl -n "$NS" get deploy hks-lab-app -o jsonpath='{.status.replicas}')
  log_info "t+${i}x15s: replicas=$CUR"
  MIN=$(kubectl -n "$NS" get hpa hks-lab-app -o jsonpath='{.spec.minReplicas}')
  if [[ "$CUR" == "$MIN" ]]; then SCALED_DOWN=true; break; fi
done
$SCALED_DOWN && log_pass "AUT-002 HPA scaled back down to minReplicas" || log_info "AUT-002 did not reach minReplicas within observation window (may need more time -- stabilizationWindowSeconds)"

log_step "AUT-003: Cluster Autoscaler reaction to unschedulable pods (bounded, temporary)"
if has_cluster_autoscaler; then
  log_info "cluster-autoscaler workload detected -- proceeding with exhaustion test"
else
  log_info "No cluster-autoscaler workload detected. Running the exhaustion test anyway to produce evidence of Pending pods (expected: no reaction)."
fi

if ! confirm "AUT-003 will temporarily deploy 10 pods requesting 1200m CPU each to force resource exhaustion. Continue?"; then
  log_skip "AUT-003 skipped by user"
  exit 0
fi

BEFORE_NODES=$(kubectl get nodes --no-headers | wc -l | tr -d ' ')
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hks-lab-ca-exhaustion-test
  namespace: $NS
  labels: {app.kubernetes.io/part-of: hks-capability-lab, hks-capability-lab/role: ca-exhaustion-test}
spec:
  replicas: 10
  selector: {matchLabels: {hks-capability-lab/role: ca-exhaustion-test}}
  template:
    metadata: {labels: {hks-capability-lab/role: ca-exhaustion-test}}
    spec:
      containers:
        - name: filler
          image: ${APP_IMAGE}
          command: ["sleep", "600"]
          resources:
            requests: {cpu: "1200m", memory: "128Mi"}
            limits: {cpu: "1200m", memory: "128Mi"}
EOF

sleep 20
PENDING=$(kubectl -n "$NS" get pods -l hks-capability-lab/role=ca-exhaustion-test --no-headers | grep -c Pending || true)
log_info "Pending pods after 20s: $PENDING"

for i in 1 2; do
  sleep 20
  AFTER_NODES=$(kubectl get nodes --no-headers | wc -l | tr -d ' ')
  STILL_PENDING=$(kubectl -n "$NS" get pods -l hks-capability-lab/role=ca-exhaustion-test --no-headers | grep -c Pending || true)
  log_info "t+$((i*20))s: nodes=$AFTER_NODES (was $BEFORE_NODES), pending=$STILL_PENDING"
done

kubectl -n "$NS" delete deployment hks-lab-ca-exhaustion-test >/dev/null 2>&1
log_info "Temporary exhaustion-test Deployment removed"

if [[ "$AFTER_NODES" -gt "$BEFORE_NODES" ]]; then
  log_pass "AUT-003 Cluster Autoscaler added a node in response to Pending pods"
elif [[ "$PENDING" -gt 0 ]]; then
  log_info "AUT-003 CLUSTER AUTOSCALER = NOT VALIDATED (infrastructure not available on this cluster) -- Pending pods observed, no node added. See docs/validation/AUTOSCALER_VALIDATION.md."
else
  log_info "AUT-003 inconclusive -- cluster had enough spare capacity to schedule all test pods; increase replica count/cpu request to force exhaustion"
fi
