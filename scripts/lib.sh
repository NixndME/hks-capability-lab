#!/usr/bin/env bash
# Shared helpers for run-hks-test.sh and scripts/validate-*.sh.
# Sourced, never executed directly.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE_DIR="$REPO_ROOT/evidence"
RESULTS_LOG="$EVIDENCE_DIR/test-run-$(date -u +%Y%m%dT%H%M%SZ).log"
mkdir -p "$EVIDENCE_DIR"

C_RESET="\033[0m"; C_GREEN="\033[32m"; C_RED="\033[31m"; C_YELLOW="\033[33m"; C_BLUE="\033[34m"; C_BOLD="\033[1m"

log()      { echo -e "$*" | tee -a "$RESULTS_LOG"; }
log_pass() { log "${C_GREEN}PASS${C_RESET}  $*"; }
log_fail() { log "${C_RED}FAIL${C_RESET}  $*"; }
log_skip() { log "${C_YELLOW}SKIP${C_RESET}  $*"; }
log_info() { log "${C_BLUE}INFO${C_RESET}  $*"; }
log_step() { log "\n${C_BOLD}== $* ==${C_RESET}"; }

require_config() {
  if [[ ! -f "$REPO_ROOT/config.env" ]]; then
    echo "config.env not found. Run: cp config.env.example config.env" >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "$REPO_ROOT/config.env"
  set +a
}

# Populate/refresh values that config.env allows to be "auto".
resolve_auto_config() {
  if [[ "${STORAGE_CLASS:-auto}" == "auto" ]]; then
    local default_sc
    default_sc=$(kubectl get sc -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}' 2>/dev/null)
    if [[ -z "$default_sc" ]]; then
      local count
      count=$(kubectl get sc -o name 2>/dev/null | wc -l | tr -d ' ')
      if [[ "$count" == "1" ]]; then
        default_sc=$(kubectl get sc -o jsonpath='{.items[0].metadata.name}')
      fi
    fi
    if [[ -z "$default_sc" ]]; then
      log_fail "STORAGE_CLASS=auto but no default StorageClass and more than one StorageClass exists. Set STORAGE_CLASS explicitly in config.env."
      exit 1
    fi
    export STORAGE_CLASS="$default_sc"
    log_info "Resolved STORAGE_CLASS=auto -> $STORAGE_CLASS"
  fi

  if [[ "${INGRESS_CLASS:-auto}" == "auto" ]]; then
    local ic
    ic=$(kubectl get ingressclass -o jsonpath='{.items[?(@.metadata.annotations.ingressclass\.kubernetes\.io/is-default-class=="true")].metadata.name}' 2>/dev/null)
    if [[ -z "$ic" ]]; then
      local count
      count=$(kubectl get ingressclass -o name 2>/dev/null | wc -l | tr -d ' ')
      if [[ "$count" == "1" ]]; then
        ic=$(kubectl get ingressclass -o jsonpath='{.items[0].metadata.name}')
      fi
    fi
    export INGRESS_CLASS="${ic:-}"
    [[ -n "$ic" ]] && log_info "Resolved INGRESS_CLASS=auto -> $INGRESS_CLASS"
  fi

  # Prometheus namespace/ServiceAccount, needed for the scrape-access RoleBinding.
  if kubectl get crd prometheuses.monitoring.coreos.com >/dev/null 2>&1; then
    local ns name sa
    read -r ns name <<<"$(kubectl get prometheus -A --no-headers 2>/dev/null | awk '{print $1, $2}' | head -1)"
    if [[ -n "${ns:-}" && -n "${name:-}" ]]; then
      sa=$(kubectl -n "$ns" get prometheus "$name" -o jsonpath='{.spec.serviceAccountName}' 2>/dev/null)
      export PROMETHEUS_NAMESPACE="$ns"
      export PROMETHEUS_SERVICEACCOUNT="${sa:-prometheus-k8s}"
      log_info "Resolved Prometheus ServiceAccount -> $PROMETHEUS_NAMESPACE/$PROMETHEUS_SERVICEACCOUNT"
    fi
  else
    export PROMETHEUS_NAMESPACE="none"
    export PROMETHEUS_SERVICEACCOUNT="none"
  fi
}

ENVSUBST_VARS='$NAMESPACE $STORAGE_CLASS $TEST_HOST $APP_IMAGE $APP_REPLICAS $INGRESS_CLASS $PROMETHEUS_NAMESPACE $PROMETHEUS_SERVICEACCOUNT'

# render_apply <file>: envsubst the known variable set only (never touches
# unrelated $ characters, e.g. inside the embedded app code) and apply it.
render_apply() {
  local file="$1"
  envsubst "$ENVSUBST_VARS" < "$file" | kubectl apply -f -
}

render_delete() {
  local file="$1"
  envsubst "$ENVSUBST_VARS" < "$file" | kubectl delete --ignore-not-found=true -f -
}

# --- capability discovery (cached in-process) ---
has_crd()          { kubectl get crd "$1" >/dev/null 2>&1; }
has_gateway_api()  { kubectl get crd gateways.gateway.networking.k8s.io >/dev/null 2>&1; }
has_prometheus_operator() { has_crd servicemonitors.monitoring.coreos.com; }
has_metrics_api()  { kubectl get apiservices v1beta1.metrics.k8s.io -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null | grep -q True; }
has_cluster_autoscaler() { kubectl get pods -A --no-headers 2>/dev/null | grep -qi 'cluster-autoscaler'; }
loadbalancer_works() {
  local ext
  ext=$(kubectl get svc -A -o jsonpath='{range .items[?(@.spec.type=="LoadBalancer")]}{.status.loadBalancer.ingress}{"\n"}{end}' 2>/dev/null | grep -v '^$')
  [[ -n "$ext" ]]
}

wait_rollout() {
  local ns="$1" dep="$2" timeout="${3:-120s}"
  kubectl -n "$ns" rollout status "deployment/$dep" --timeout="$timeout"
}

confirm() {
  local prompt="$1"
  read -r -p "$prompt [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]]
}
