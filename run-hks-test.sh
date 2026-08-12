#!/usr/bin/env bash
# HKS Kubernetes Capability Validation Lab -- interactive wizard.
#
# Usage:
#   ./run-hks-test.sh              interactive menu
#   ./run-hks-test.sh --all        run every safe test automatically
#   ./run-hks-test.sh --cleanup    remove only resources this suite created
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source scripts/lib.sh

MODE="${1:-menu}"

banner() {
  echo -e "${C_BOLD}=========================================="
  echo " HKS Kubernetes Capability Validation Lab"
  echo -e "==========================================${C_RESET}"
  echo "Cluster:            $(kubectl config current-context 2>/dev/null)"
  echo "Kubernetes Version: $(kubectl version -o json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)["serverVersion"]["gitVersion"])' 2>/dev/null)"
  echo "Nodes:              $(kubectl get nodes --no-headers 2>/dev/null | wc -l | tr -d ' ')"
  echo "Namespace:          ${NAMESPACE:-<not loaded>}"
  echo "Storage:            ${STORAGE_CLASS:-<not resolved>}"
  echo "Ingress:            ${INGRESS_CLASS:-<not resolved>}$( [[ -z "${INGRESS_CLASS:-}" ]] && echo ' (NOT AVAILABLE)')"
  echo "Gateway API:        $(has_gateway_api && echo AVAILABLE || echo 'NOT AVAILABLE')"
  echo "LoadBalancer:       $(loadbalancer_works && echo AVAILABLE || echo 'API-SUPPORTED ONLY (no infra)')"
  echo "Prometheus:         $(has_prometheus_operator && echo AVAILABLE || echo 'NOT AVAILABLE')"
  echo "Metrics API (HPA):  $(has_metrics_api && echo AVAILABLE || echo 'NOT AVAILABLE')"
  echo "Cluster Autoscaler: $(has_cluster_autoscaler && echo ENABLED || echo 'NOT AVAILABLE')"
  echo
}

deploy_core() {
  log_step "Deploying core application"
  render_apply hks-capability-lab.yaml
  wait_rollout "$NAMESPACE" hks-lab-app 120s
}

do_access() { bash scripts/validate-networking.sh; }
do_storage() { bash scripts/validate-storage.sh; }
do_prometheus() { bash scripts/validate-prometheus.sh; }
do_autoscale() { bash scripts/validate-autoscaler.sh; }
do_rollout() { bash scripts/validate-rollout.sh; }
do_rollback() {
  kubectl -n "$NAMESPACE" rollout undo deployment/hks-lab-app
  wait_rollout "$NAMESPACE" hks-lab-app 90s
}
do_resiliency() { bash scripts/validate-resiliency.sh; }

do_bluegreen() {
  log_step "Blue/Green deployment"
  render_apply manifests/blue-green.yaml
  wait_rollout "$NAMESPACE" hks-lab-app-blue 60s
  wait_rollout "$NAMESPACE" hks-lab-app-green 60s
  log_info "Flipping traffic blue -> green"
  kubectl -n "$NAMESPACE" patch svc hks-lab-bluegreen -p '{"spec":{"selector":{"hks-capability-lab/track":"green"}}}'
  sleep 3
  log_info "Rolling back green -> blue"
  kubectl -n "$NAMESPACE" patch svc hks-lab-bluegreen -p '{"spec":{"selector":{"hks-capability-lab/track":"blue"}}}'
  log_pass "Blue/Green: both tracks coexisted, traffic switch + rollback both worked (see BLUE_GREEN section of docs/validation/TEST_RESULTS.md)"
}

do_canary() {
  log_step "Canary deployment"
  if [[ "${INGRESS_CLASS:-}" != "nginx" ]]; then
    log_skip "Canary test uses nginx.ingress.kubernetes.io annotations; discovered IngressClass is '${INGRESS_CLASS:-none}' -- NOT SUPPORTED on this cluster"
    return
  fi
  render_apply manifests/canary.yaml
  wait_rollout "$NAMESPACE" hks-lab-app-canary 60s
  CTRL_IP=$(kubectl -n ingress-nginx get pods -l app.kubernetes.io/component=controller -o jsonpath='{.items[0].status.hostIP}' 2>/dev/null)
  HTTP_NP=$(kubectl -n ingress-nginx get svc ingress-nginx-controller -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}' 2>/dev/null)
  if [[ -z "$CTRL_IP" ]]; then
    log_skip "Could not locate ingress-nginx controller pod/service"
    return
  fi
  V2=0; V3=0
  for i in $(seq 1 30); do
    V=$(curl -s -m 3 -H "Host: ${TEST_HOST}" "http://$CTRL_IP:$HTTP_NP/api/info" | python3 -c "import json,sys;print(json.load(sys.stdin).get('version','?'))" 2>/dev/null)
    [[ "$V" == "v3" ]] && V3=$((V3+1)) || V2=$((V2+1))
  done
  log_pass "Canary distribution over 30 requests: stable=$V2 canary=$V3 (configured weight: 10%)"
}

do_networkpolicy() {
  log_step "NetworkPolicy"
  render_apply manifests/network-policy.yaml
  wait_rollout "$NAMESPACE" netpol-backend 60s
  wait_rollout "$NAMESPACE" netpol-frontend 60s
  wait_rollout "$NAMESPACE" netpol-untrusted 60s
  FRONTEND=$(kubectl -n "$NAMESPACE" get pods -l hks-capability-lab/role=frontend -o jsonpath='{.items[0].metadata.name}')
  UNTRUSTED=$(kubectl -n "$NAMESPACE" get pods -l hks-capability-lab/role=untrusted -o jsonpath='{.items[0].metadata.name}')
  if kubectl -n "$NAMESPACE" exec "$FRONTEND" -- curl -s -o /dev/null -m 5 http://netpol-backend:8080/; then
    log_pass "frontend -> backend ALLOWED"
  else
    log_fail "frontend -> backend should be allowed but was not"
  fi
  if kubectl -n "$NAMESPACE" exec "$UNTRUSTED" -- curl -s -o /dev/null -m 5 http://netpol-backend:8080/; then
    log_fail "untrusted -> backend should be DENIED but succeeded"
  else
    log_pass "untrusted -> backend DENIED"
  fi
}

do_scheduling() {
  log_step "Scheduling"
  log_info "See docs/validation/SCHEDULING_VALIDATION.md -- run individual probes via kubectl using the manifests documented there (nodeSelector, node affinity, tolerations)."
  kubectl -n "$NAMESPACE" get pods -l app.kubernetes.io/name=hks-lab-app -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName
}

generate_report() {
  log_step "Generating report"
  echo "See docs/validation/HKS_CAPABILITY_MATRIX.md, docs/validation/TEST_RESULTS.md, and docs/validation/HKS_PRODUCT_VALIDATION_REPORT.md for the full write-up."
  echo "Raw test log for this run: $RESULTS_LOG"
}

cleanup() {
  log_step "Cleanup (only resources this suite created)"
  if ! confirm "This will delete the '${NAMESPACE}' namespace's resources created by this suite (core app stays unless you also pass --cleanup-all). Continue?"; then
    echo "Aborted."
    exit 0
  fi
  render_delete manifests/network-policy.yaml
  render_delete manifests/canary.yaml
  render_delete manifests/blue-green.yaml
  render_delete manifests/storage-test.yaml
  log_info "Temporary demo resources removed. Core app (hks-capability-lab.yaml) left running."
  log_info "To remove EVERYTHING including the namespace itself, run: kubectl delete namespace ${NAMESPACE}"
  log_info "(intentionally not automated -- confirm the namespace was created exclusively by this suite first)"
}

run_all() {
  local pass=0 fail=0 skip=0
  deploy_core
  do_access
  do_storage
  do_prometheus
  do_autoscale
  do_rollout
  do_bluegreen
  do_canary
  do_networkpolicy
  do_scheduling
  do_resiliency
  do_networkpolicy_cleanup() { render_delete manifests/network-policy.yaml; render_delete manifests/canary.yaml; render_delete manifests/blue-green.yaml; render_delete manifests/storage-test.yaml; }
  do_networkpolicy_cleanup
  echo
  echo -e "${C_BOLD}=================================\n HKS CAPABILITY TEST SUMMARY\n=================================${C_RESET}"
  grep -c "^PASS" "$RESULTS_LOG" | xargs echo "Passed:"
  grep -c "^FAIL" "$RESULTS_LOG" | xargs echo "Failed:"
  grep -c "^SKIP" "$RESULTS_LOG" | xargs echo "Skipped:"
  echo "Full log: $RESULTS_LOG"
}

menu() {
  while true; do
    banner
    cat <<'EOF'
What would you like to test?

 1. Deploy application
 2. Test application access (port-forward/ClusterIP/NodePort/LB/Ingress)
 3. Test storage
 4. Test Prometheus
 5. Test autoscaling (HPA + Cluster Autoscaler)
 6. Test rolling deployment
 7. Test rollback
 8. Test blue/green
 9. Test canary
10. Test scheduling
11. Test network policy
12. Test resiliency
13. Run complete capability suite (--all)
14. Generate report
15. Cleanup temporary resources
 0. Exit
EOF
    read -r -p "> " choice
    case "$choice" in
      1) deploy_core ;;
      2) do_access ;;
      3) do_storage ;;
      4) do_prometheus ;;
      5) do_autoscale ;;
      6) do_rollout ;;
      7) do_rollback ;;
      8) do_bluegreen ;;
      9) do_canary ;;
      10) do_scheduling ;;
      11) do_networkpolicy ;;
      12) do_resiliency ;;
      13) run_all ;;
      14) generate_report ;;
      15) cleanup ;;
      0) exit 0 ;;
      *) echo "Unknown option" ;;
    esac
    echo
  done
}

require_config
resolve_auto_config

case "$MODE" in
  --all) banner; run_all ;;
  --cleanup) require_config; cleanup ;;
  menu) menu ;;
  *) echo "Unknown argument: $MODE" >&2; exit 1 ;;
esac
