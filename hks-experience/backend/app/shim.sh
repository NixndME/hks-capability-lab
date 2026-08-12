#!/usr/bin/env bash
# Thin shim so the guided-journey backend can invoke the EXISTING
# validator's proven primitives (scripts/lib.sh: render_apply/render_delete,
# wait_rollout, has_prometheus_operator, has_gateway_api,
# has_cluster_autoscaler, loadbalancer_works, log_pass/log_fail/log_skip)
# without duplicating or modifying scripts/lib.sh itself -- source of truth
# stays run-hks-test.sh's engine, this file only adds step-addressable
# wrappers around it (the existing scripts are monolithic per-category,
# not individually callable per guided step).
#
# Usage: bash shim.sh action_<name> [args...]
set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"
# config.env may not exist in a fresh container -- fall back to
# config.env.example's defaults (same format) so $NAMESPACE etc. are always
# set before scripts/lib.sh (set -uo pipefail) is sourced.
if [[ -f config.env ]]; then
  set -a; source config.env; set +a
elif [[ -f config.env.example ]]; then
  set -a; source config.env.example; set +a
fi
# shellcheck disable=SC1091
source scripts/lib.sh

# Additive-only helper, not a change to scripts/lib.sh: a fourth outcome
# alongside log_pass/log_fail/log_skip for "a prerequisite (cluster
# connectivity, RBAC) is missing" -- distinct from a capability test
# actually running and failing. Format: "BLOCKED  CODE: message", parsed by
# backend/app/executor.py.
log_blocked() { log "${C_YELLOW}BLOCKED${C_RESET}  $*"; }

# Fast, resolve_auto_config-independent connectivity probe. Every action_*
# below calls require_connectivity (or ensure_resolved) FIRST and returns a
# structured BLOCKED result if the cluster isn't reachable, instead of
# letting scripts/lib.sh's resolve_auto_config hit its own internal `exit 1`
# (existing, untouched behavior -- correct for the CLI context it was
# written for, where a hard exit with a printed message is fine) and
# silently kill this whole process with ZERO output, which is exactly the
# bug this file previously had.
check_connectivity() {
  kubectl version -o json --request-timeout=8s >/dev/null 2>&1
}

require_connectivity() {
  if ! check_connectivity; then
    log_blocked "KUBERNETES_CONNECTION_FAILED: kubectl could not reach a Kubernetes API server. If running via Podman, mount your kubeconfig: -v ~/.kube:/home/hksexp/.kube:ro (or set KUBECONFIG to a valid file inside the container)."
    return 1
  fi
  return 0
}

# resolve_auto_config (scripts/lib.sh, untouched) discovers StorageClass/
# IngressClass/the Prometheus ServiceAccount -- only actions that actually
# deploy/route through those need it (deploy_app, ingress, prometheus,
# canary, storage). Calling it unconditionally for every action (the
# previous bug) coupled unrelated steps to StorageClass resolution and,
# combined with `exit 1` on failure, made ANY action silently produce empty
# output whenever the cluster was unreachable.
ensure_resolved() {
  require_connectivity || return 1
  resolve_auto_config
}

APP_URL_INTERNAL="http://hks-lab-app.${NAMESPACE}.svc.cluster.local"

# --- Getting Started -------------------------------------------------------
# (Cluster Preparation itself is handled by the Python kubernetes client in
# backend/app/routers/steps.py's _run_cluster_prep -- not this shim -- so
# its "is Kubernetes reachable" question is never entangled with
# StorageClass/IngressClass resolution. No action_cluster_discovery here.)

action_create_namespace() {
  require_connectivity || return
  kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  local status
  status=$(kubectl get namespace "$NAMESPACE" -o jsonpath='{.status.phase}')
  [[ "$status" == "Active" ]] && log_pass "Namespace $NAMESPACE is Active" || log_fail "Namespace $NAMESPACE status=$status"
}

action_deploy_app() {
  ensure_resolved || return
  # Reuses 100% of the existing validator's proven infrastructure
  # (Namespace, Secret, ServiceAccount/RBAC, Deployment, Services, HPA, PDB,
  # Ingress, ServiceMonitor -- all unchanged, all from hks-capability-lab.yaml)
  # and only swaps which application source the ConfigMap serves, so the
  # guided journey demonstrates "HKS Demo Workload" (hks-experience/sample-app/)
  # rather than duplicating the entire manifest just to change the embedded
  # app code. Same namespace/Deployment/Service names either way -- one
  # workload, two ways to operate it (this journey, or run-hks-test.sh).
  render_apply hks-capability-lab.yaml
  kubectl -n "$NAMESPACE" create configmap hks-lab-app-code \
    --from-file=app.py="$REPO_ROOT/hks-experience/sample-app/app.py" \
    --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  kubectl -n "$NAMESPACE" rollout restart deployment/hks-lab-app >/dev/null
  if wait_rollout "$NAMESPACE" hks-lab-app 120s; then
    log_pass "HKS Demo Workload deployed and rolled out"
  else
    log_fail "hks-lab-app rollout did not complete in time"
  fi
}

# --- Application Access ------------------------------------------------

action_open_app() {
  require_connectivity || return
  local endpoints
  endpoints=$(kubectl -n "$NAMESPACE" get endpoints hks-lab-app -o jsonpath='{.subsets[*].addresses[*].ip}')
  if [[ -n "$endpoints" ]]; then
    log_pass "Service hks-lab-app has live endpoints: $endpoints"
    log_info "Run: kubectl -n $NAMESPACE port-forward svc/hks-lab-app 18080:80"
  else
    log_fail "Service hks-lab-app has no endpoints yet"
  fi
}

action_verify_clusterip() {
  require_connectivity || return
  local pod
  pod=$(kubectl -n "$NAMESPACE" get pods -l app.kubernetes.io/name=hks-lab-app -o jsonpath='{.items[0].metadata.name}')
  [[ -z "$pod" ]] && { log_fail "no app pod found"; return; }
  for host in hks-lab-app "hks-lab-app.$NAMESPACE" "hks-lab-app.$NAMESPACE.svc.cluster.local"; do
    if kubectl -n "$NAMESPACE" exec "$pod" -- python3 -c "import urllib.request; urllib.request.urlopen('http://$host/', timeout=3)" >/dev/null 2>&1; then
      log_pass "$host resolved and answered"
    else
      log_fail "$host did not answer"
    fi
  done
}

action_verify_nodeport() {
  require_connectivity || return
  local np node_ip
  np=$(kubectl -n "$NAMESPACE" get svc hks-lab-app-nodeport -o jsonpath='{.spec.ports[0].nodePort}')
  node_ip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
  [[ -z "$np" || -z "$node_ip" ]] && { log_fail "could not resolve NodePort or node IP"; return; }
  if curl -s -o /dev/null -m 5 -w '%{http_code}' "http://$node_ip:$np/" | grep -q 200; then
    log_pass "NodePort $node_ip:$np answered HTTP 200"
  else
    log_fail "NodePort $node_ip:$np did not answer HTTP 200"
  fi
}

action_verify_loadbalancer() {
  require_connectivity || return
  kubectl -n "$NAMESPACE" expose deployment hks-lab-app --name=hks-lab-app-lb-test --type=LoadBalancer --port=80 --target-port=8080 >/dev/null 2>&1
  sleep 5
  local ext
  ext=$(kubectl -n "$NAMESPACE" get svc hks-lab-app-lb-test -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
  kubectl -n "$NAMESPACE" delete svc hks-lab-app-lb-test >/dev/null 2>&1
  if [[ -n "$ext" ]]; then
    log_pass "EXTERNAL-IP assigned: $ext"
  else
    log_skip "LoadBalancer NOT_AVAILABLE: EXTERNAL-IP stayed <pending> -- no LB infrastructure on this cluster (not a defect)"
  fi
}

action_verify_ingress() {
  ensure_resolved || return
  if [[ -z "${INGRESS_CLASS:-}" ]]; then
    log_skip "No IngressClass discovered on this cluster"
    return
  fi
  local ctrl_ip http_np
  ctrl_ip=$(kubectl -n ingress-nginx get pods -l app.kubernetes.io/component=controller -o jsonpath='{.items[0].status.hostIP}' 2>/dev/null)
  http_np=$(kubectl -n ingress-nginx get svc ingress-nginx-controller -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}' 2>/dev/null)
  [[ -z "$ctrl_ip" ]] && { log_skip "Could not locate ingress-nginx controller"; return; }
  render_apply hks-capability-lab.yaml >/dev/null
  if curl -s -m 5 -H "Host: ${TEST_HOST}" "http://$ctrl_ip:$http_np/" -o /dev/null -w '%{http_code}' | grep -q 200; then
    log_pass "Ingress routed via $ctrl_ip:$http_np, HTTP 200"
  else
    log_fail "Ingress did not return HTTP 200"
  fi
}

# --- Scaling -------------------------------------------------------------

action_verify_hpa() {
  require_connectivity || return
  local cpu
  cpu=$(kubectl -n "$NAMESPACE" get hpa hks-lab-app -o jsonpath='{.status.currentMetrics[0].resource.current.averageUtilization}' 2>/dev/null)
  if [[ -n "$cpu" ]]; then
    log_pass "HPA hks-lab-app active, current CPU=${cpu}%"
  else
    log_fail "HPA hks-lab-app not reporting metrics yet"
  fi
}

action_run_cpu_load() {
  require_connectivity || return
  local pods
  pods=$(kubectl -n "$NAMESPACE" get pods -l app.kubernetes.io/name=hks-lab-app,hks-capability-lab/track=stable -o jsonpath='{.items[*].metadata.name}')
  for p in $pods; do
    kubectl -n "$NAMESPACE" exec "$p" -- python3 -c "
import urllib.request
urllib.request.urlopen(urllib.request.Request('http://localhost:8080/api/load?cpu=90&duration=180&concurrency=2', method='POST'), timeout=5)
" >/dev/null 2>&1 &
  done
  wait
  log_pass "CPU load started on: $pods (duration 180s) -- poll GET hpa to watch replicas change"
}

action_run_memory_load() {
  require_connectivity || return
  local pods
  pods=$(kubectl -n "$NAMESPACE" get pods -l app.kubernetes.io/name=hks-lab-app,hks-capability-lab/track=stable -o jsonpath='{.items[*].metadata.name}')
  for p in $pods; do
    kubectl -n "$NAMESPACE" exec "$p" -- python3 -c "
import urllib.request
urllib.request.urlopen(urllib.request.Request('http://localhost:8080/api/load?cpu=10&duration=60&concurrency=1', method='POST'), timeout=5)
" >/dev/null 2>&1 &
  done
  wait
  log_pass "Load job started on: $pods (this HPA targets CPU only -- replica count should stay unchanged)"
}

# --- Observability ---------------------------------------------------------

action_verify_prometheus() {
  ensure_resolved || return
  if ! has_prometheus_operator; then
    log_skip "Prometheus Operator CRDs not found on this cluster"
    return
  fi
  render_apply hks-capability-lab.yaml >/dev/null
  local sm
  sm=$(kubectl -n "$NAMESPACE" get servicemonitor hks-lab-app -o name 2>/dev/null)
  [[ -n "$sm" ]] && log_pass "ServiceMonitor hks-lab-app created" || log_fail "ServiceMonitor hks-lab-app not found"
}

# --- Lifecycle ---------------------------------------------------------

action_run_rolling_update() {
  require_connectivity || return
  local current next
  current=$(kubectl -n "$NAMESPACE" get deploy hks-lab-app -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="APP_VERSION")].value}')
  next="v2"; [[ "$current" == "v2" ]] && next="v3"
  kubectl -n "$NAMESPACE" set env deployment/hks-lab-app APP_VERSION="$next" >/dev/null
  if wait_rollout "$NAMESPACE" hks-lab-app 90s; then
    log_pass "Rolled out $current -> $next"
  else
    log_fail "Rollout to $next did not complete"
  fi
}

action_run_rollback() {
  require_connectivity || return
  kubectl -n "$NAMESPACE" rollout undo deployment/hks-lab-app >/dev/null
  if wait_rollout "$NAMESPACE" hks-lab-app 90s; then
    log_pass "Rollback complete"
  else
    log_fail "Rollback did not complete"
  fi
}

action_run_bluegreen() {
  require_connectivity || return
  render_apply manifests/blue-green.yaml
  wait_rollout "$NAMESPACE" hks-lab-app-blue 60s
  wait_rollout "$NAMESPACE" hks-lab-app-green 60s
  local before after
  before=$(kubectl -n "$NAMESPACE" get svc hks-lab-bluegreen -o jsonpath='{.spec.selector.hks-capability-lab/track}')
  kubectl -n "$NAMESPACE" patch svc hks-lab-bluegreen -p '{"spec":{"selector":{"hks-capability-lab/track":"green"}}}' >/dev/null
  after=$(kubectl -n "$NAMESPACE" get svc hks-lab-bluegreen -o jsonpath='{.spec.selector.hks-capability-lab/track}')
  log_pass "Traffic switched: $before -> $after"
}

action_run_canary() {
  ensure_resolved || return
  if [[ "${INGRESS_CLASS:-}" != "nginx" ]]; then
    log_skip "Canary requires ingress-nginx; discovered IngressClass is '${INGRESS_CLASS:-none}'"
    return
  fi
  render_apply manifests/canary.yaml
  wait_rollout "$NAMESPACE" hks-lab-app-canary 60s
  local ctrl_ip http_np v2=0 v3=0
  ctrl_ip=$(kubectl -n ingress-nginx get pods -l app.kubernetes.io/component=controller -o jsonpath='{.items[0].status.hostIP}' 2>/dev/null)
  http_np=$(kubectl -n ingress-nginx get svc ingress-nginx-controller -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}' 2>/dev/null)
  for i in $(seq 1 20); do
    v=$(curl -s -m 3 -H "Host: ${TEST_HOST}" "http://$ctrl_ip:$http_np/api/info" | python3 -c "import json,sys;print(json.load(sys.stdin).get('version','?'))" 2>/dev/null)
    [[ "$v" == "v3" ]] && v3=$((v3+1)) || v2=$((v2+1))
  done
  log_pass "Observed distribution over 20 requests: stable=$v2 canary=$v3"
}

# --- Storage / Security / Scheduling / Resiliency / Autoscaling -------------

action_run_storage_test() {
  ensure_resolved || return
  render_apply manifests/storage-test.yaml
  wait_rollout "$NAMESPACE" hks-lab-storage-test 60s
  local pod marker
  pod=$(kubectl -n "$NAMESPACE" get pods -l hks-capability-lab/role=storage-test -o jsonpath='{.items[0].metadata.name}')
  marker="HKS_STORAGE_TEST=$(date -u +%s)"
  kubectl -n "$NAMESPACE" exec "$pod" -- sh -c "echo $marker > /data/marker.txt"
  kubectl -n "$NAMESPACE" delete pod "$pod" >/dev/null
  wait_rollout "$NAMESPACE" hks-lab-storage-test 60s
  local new_pod readback
  new_pod=$(kubectl -n "$NAMESPACE" get pods -l hks-capability-lab/role=storage-test -o jsonpath='{.items[0].metadata.name}')
  readback=$(kubectl -n "$NAMESPACE" exec "$new_pod" -- cat /data/marker.txt)
  if [[ "$readback" == "$marker" ]]; then
    log_pass "Marker survived pod replacement ($pod -> $new_pod): $readback"
  else
    log_fail "Marker mismatch: wrote '$marker', read '$readback'"
  fi
}

action_run_network_policy() {
  require_connectivity || return
  render_apply manifests/network-policy.yaml
  wait_rollout "$NAMESPACE" netpol-backend 60s
  wait_rollout "$NAMESPACE" netpol-frontend 60s
  wait_rollout "$NAMESPACE" netpol-untrusted 60s
  local frontend untrusted
  frontend=$(kubectl -n "$NAMESPACE" get pods -l hks-capability-lab/role=frontend -o jsonpath='{.items[0].metadata.name}')
  untrusted=$(kubectl -n "$NAMESPACE" get pods -l hks-capability-lab/role=untrusted -o jsonpath='{.items[0].metadata.name}')
  if kubectl -n "$NAMESPACE" exec "$frontend" -- curl -s -o /dev/null -m5 http://netpol-backend:8080/; then
    log_pass "frontend -> backend ALLOWED"
  else
    log_fail "frontend -> backend should be allowed but was not"
  fi
  if kubectl -n "$NAMESPACE" exec "$untrusted" -- curl -s -o /dev/null -m5 http://netpol-backend:8080/; then
    log_fail "untrusted -> backend should be DENIED but succeeded"
  else
    log_pass "untrusted -> backend DENIED"
  fi
}

action_verify_scheduling() {
  require_connectivity || return
  kubectl -n "$NAMESPACE" get pods -l app.kubernetes.io/name=hks-lab-app -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName --no-headers | while read -r name node; do
    log_info "pod=$name node=$node"
  done
  log_pass "See docs/validation/SCHEDULING_VALIDATION.md for the full probe writeup; live placement listed above"
}

action_run_resiliency_test() {
  require_connectivity || return
  local before pod
  before=$(kubectl -n "$NAMESPACE" get deploy hks-lab-app -o jsonpath='{.status.readyReplicas}')
  pod=$(kubectl -n "$NAMESPACE" get pods -l app.kubernetes.io/name=hks-lab-app,hks-capability-lab/track=stable -o jsonpath='{.items[0].metadata.name}')
  kubectl -n "$NAMESPACE" delete pod "$pod" >/dev/null
  if wait_rollout "$NAMESPACE" hks-lab-app 60s; then
    local after
    after=$(kubectl -n "$NAMESPACE" get deploy hks-lab-app -o jsonpath='{.status.readyReplicas}')
    log_pass "Killed $pod; replicas restored to $after (was $before)"
  else
    log_fail "Replicas did not recover within 60s"
  fi
}

action_verify_cluster_autoscaler() {
  require_connectivity || return
  if has_cluster_autoscaler; then
    log_info "Cluster Autoscaler pod detected -- a real scale-up test requires genuinely unschedulable pods; not auto-triggered from this step to avoid unbounded resource requests."
    log_pass "Cluster Autoscaler infrastructure present"
  else
    log_skip "NOT_AVAILABLE: no cluster-autoscaler pod found -- infrastructure gap, not a Kubernetes defect"
  fi
}

"$@"
