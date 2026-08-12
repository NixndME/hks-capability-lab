#!/usr/bin/env bash
# Validates every application access mode the cluster actually supports:
# port-forward, ClusterIP (in-cluster DNS), NodePort, LoadBalancer (API vs
# infra), and Ingress. Determines public/private/local scope of whatever
# address it finds. Cleans up only the temporary resources it creates.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/lib.sh
require_config
resolve_auto_config

NS="$NAMESPACE"
OUT="$EVIDENCE_DIR/access-modes-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT"

is_private_ip() {
  local ip="$1"
  [[ "$ip" =~ ^10\. ]] && return 0
  [[ "$ip" =~ ^192\.168\. ]] && return 0
  [[ "$ip" =~ ^127\. ]] && return 0
  [[ "$ip" =~ ^169\.254\. ]] && return 0
  if [[ "$ip" =~ ^172\.([0-9]+)\. ]]; then
    local second="${BASH_REMATCH[1]}"
    [[ "$second" -ge 16 && "$second" -le 31 ]] && return 0
  fi
  return 1
}
describe_scope() {
  local ip="$1"
  if is_private_ip "$ip"; then echo "PRIVATE (RFC1918/loopback/link-local)"; else echo "PUBLIC (routable)"; fi
}

log_step "NET-001: Port-forward"
kubectl -n "$NS" port-forward svc/hks-lab-app 18080:80 >/dev/null 2>&1 &
PF_PID=$!
sleep 2
if curl -s -o /dev/null -m 5 -w '' "http://localhost:18080/"; then
  log_pass "NET-001 port-forward -> http://localhost:18080/ (scope: Local machine only)"
else
  log_fail "NET-001 port-forward did not respond"
fi
kill "$PF_PID" 2>/dev/null

log_step "NET-002: ClusterIP / in-cluster DNS"
POD=$(kubectl -n "$NS" get pods -l app.kubernetes.io/name=hks-lab-app -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [[ -n "$POD" ]]; then
  if kubectl -n "$NS" exec "$POD" -- python3 -c "import urllib.request; urllib.request.urlopen('http://hks-lab-app.$NS.svc.cluster.local/healthz', timeout=3)" >/dev/null 2>&1; then
    log_pass "NET-002 ClusterIP DNS (hks-lab-app.$NS.svc.cluster.local) reachable from within cluster (scope: Private/in-cluster)"
  else
    log_fail "NET-002 ClusterIP DNS not reachable from within the cluster"
  fi
else
  log_skip "NET-002 no running app pod found"
fi

log_step "NET-003: NodePort"
NODEPORT=$(kubectl -n "$NS" get svc hks-lab-app-nodeport -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
if [[ -n "$NODEPORT" ]]; then
  ANY_OK=false
  for ip in $(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}'); do
    code=$(curl -s -o /dev/null -m 3 -w '%{http_code}' "http://$ip:$NODEPORT/" || echo ERR)
    scope=$(describe_scope "$ip")
    if [[ "$code" == "200" ]]; then
      log_pass "NET-003 NodePort http://$ip:$NODEPORT/ -> HTTP $code (scope: $scope)"
      ANY_OK=true
    else
      log_info "NET-003 NodePort http://$ip:$NODEPORT/ -> $code"
    fi
  done
  $ANY_OK || log_fail "NET-003 NodePort did not respond on any node IP"
else
  log_skip "NET-003 hks-lab-app-nodeport service not found"
fi

log_step "NET-004: LoadBalancer (API support vs infrastructure)"
TMP_SVC="hks-lab-lb-probe"
kubectl -n "$NS" expose deployment hks-lab-app --name="$TMP_SVC" --port=80 --target-port=8080 --type=LoadBalancer >/dev/null
sleep 5
EXT=$(kubectl -n "$NS" get svc "$TMP_SVC" -o jsonpath='{.status.loadBalancer.ingress[0].ip}{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
if [[ -n "$EXT" ]]; then
  log_pass "NET-004 LoadBalancer received external address: $EXT"
else
  log_info "NET-004 LOADBALANCER = API SUPPORTED / INFRASTRUCTURE = NOT AVAILABLE (external address stayed <pending>)"
fi
kubectl -n "$NS" delete svc "$TMP_SVC" >/dev/null 2>&1

log_step "NET-005: Ingress"
if [[ -n "${INGRESS_CLASS:-}" ]]; then
  # Find a node actually running the ingress controller pod for this class,
  # since controllers with externalTrafficPolicy=Local only answer there.
  CTRL_NS=$(kubectl get pods -A -l app.kubernetes.io/component=controller -o jsonpath='{.items[0].metadata.namespace}' 2>/dev/null)
  HTTP_NP=$(kubectl -n "$CTRL_NS" get svc -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.ports[?(@.name=="http")].nodePort}{"\n"}{end}' 2>/dev/null | grep -v ' $' | head -1 | awk '{print $2}')
  CTRL_POD_IP=$(kubectl -n "$CTRL_NS" get pods -l app.kubernetes.io/component=controller -o jsonpath='{.items[0].status.hostIP}' 2>/dev/null)
  if [[ -n "$HTTP_NP" && -n "$CTRL_POD_IP" ]]; then
    code=$(curl -s -o /dev/null -m 5 -w '%{http_code}' -H "Host: ${TEST_HOST}" "http://$CTRL_POD_IP:$HTTP_NP/" || echo ERR)
    if [[ "$code" == "200" ]]; then
      log_pass "NET-005 Ingress routed correctly via http://$CTRL_POD_IP:$HTTP_NP/ (Host: $TEST_HOST)"
      log_info "DNS required for real use: $TEST_HOST -> $CTRL_POD_IP (or a real external LB/IP once available)"
    else
      log_fail "NET-005 Ingress request returned $code"
    fi
  else
    log_skip "NET-005 could not determine ingress controller NodePort/host"
  fi
else
  log_skip "NET-005 no IngressClass discovered"
fi

log_info "Evidence directory: $OUT"
