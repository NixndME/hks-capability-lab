"""Dedicated cluster connectivity + capability status, using the Kubernetes
python client only (see k8s.py). This is deliberately separate from
/api/steps/{id}/run: Cluster Preparation's own "is Kubernetes reachable"
question should never be entangled with the deploy-time machinery
(shim.sh/kubectl/envsubst) that the later mutating steps legitimately need.
"""
from fastapi import APIRouter

from .. import k8s

router = APIRouter()


@router.get("/api/cluster/status")
def cluster_status():
    cluster = k8s.discover_cluster()
    if not cluster.connected:
        return {
            "status": "blocked",
            "code": cluster.error.code if cluster.error else "KUBERNETES_CONNECTION_FAILED",
            "message": cluster.error.message if cluster.error else "Unable to connect to Kubernetes.",
            "remediation": cluster.error.remediation if cluster.error else [],
            "details": cluster.error.details if cluster.error else None,
        }

    caps = k8s.discover_capabilities()
    return {
        "status": "ready",
        "cluster": {
            "context": cluster.context,
            "version": cluster.version,
            "nodes": cluster.node_count,
        },
        "capabilities": {
            "cni": caps.cni,
            "storage": caps.storage,
            "prometheus": caps.prometheus,
            "ingress": caps.ingress,
            "gateway_api": caps.gateway_api,
            "cluster_autoscaler": caps.cluster_autoscaler,
        },
    }
