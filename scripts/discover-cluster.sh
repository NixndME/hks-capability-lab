#!/usr/bin/env bash
# Live cluster discovery. Read-only. Prints a summary and writes timestamped
# raw evidence under evidence/discovery-<timestamp>/. Safe to re-run against
# any cluster at any time -- this is how run-hks-test.sh adapts to whatever
# HKS cluster the current kubeconfig points at.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/lib.sh

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$EVIDENCE_DIR/discovery-$TS"
mkdir -p "$OUT"

log_step "Cluster identity"
kubectl version 2>&1 | tee "$OUT/version.txt"
kubectl config current-context | tee "$OUT/context.txt"

log_step "Nodes"
kubectl get nodes -o wide | tee "$OUT/nodes.txt"
NODE_COUNT=$(kubectl get nodes --no-headers | wc -l | tr -d ' ')
log_info "Node count: $NODE_COUNT"

log_step "Networking / CNI"
kubectl get pods -A -o wide | grep -iE 'calico|cilium|flannel|weave|antrea' | tee "$OUT/cni-pods.txt" || log_info "No recognized CNI pods matched by name (non-fatal; check evidence manually)"
kubectl get networkpolicies -A | tee "$OUT/networkpolicies.txt"

log_step "Ingress / Gateway API"
kubectl get ingressclass -o wide | tee "$OUT/ingressclass.txt"
if has_gateway_api; then
  log_info "Gateway API CRDs present"
  kubectl get gatewayclass,gateway -A 2>&1 | tee "$OUT/gatewayapi.txt"
else
  log_info "Gateway API CRDs NOT present"
fi

log_step "LoadBalancer"
if loadbalancer_works; then
  log_pass "At least one Service type=LoadBalancer has an external address"
else
  log_skip "No Service type=LoadBalancer currently has an external address (API-supported, infra likely unavailable)"
fi

log_step "Storage"
kubectl get storageclass -o wide | tee "$OUT/storageclass.txt"
kubectl get csidrivers | tee "$OUT/csidrivers.txt"
if kubectl get pods -A --no-headers | grep -qi 'rook-ceph'; then
  log_info "Rook/Ceph detected"
  kubectl get cephclusters.ceph.rook.io -A -o wide 2>&1 | tee "$OUT/cephclusters.txt"
else
  log_info "Rook/Ceph not detected"
fi

log_step "Prometheus"
if has_prometheus_operator; then
  log_pass "Prometheus Operator CRDs present"
  kubectl get prometheus -A -o wide | tee "$OUT/prometheus.txt"
else
  log_skip "Prometheus Operator CRDs not found"
fi
if has_metrics_api; then
  log_pass "metrics.k8s.io API is available (kubectl top / HPA resource metrics will work)"
else
  log_fail "metrics.k8s.io API not available -- HPA on CPU/memory will not function"
fi

log_step "Cluster Autoscaler"
if has_cluster_autoscaler; then
  log_pass "cluster-autoscaler workload detected"
else
  log_skip "No cluster-autoscaler workload detected (common on static/on-prem node pools)"
fi

log_step "RBAC (current identity)"
kubectl auth can-i --list 2>&1 | head -5 | tee "$OUT/rbac-self.txt"

echo "$OUT" > "$EVIDENCE_DIR/.last-discovery-path"
log_info "Raw evidence: $OUT"
