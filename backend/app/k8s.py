"""Read-only Kubernetes cluster discovery.

STRICT RULE: this module must never create/patch/delete anything. It only
ever issues get/list calls, used to answer "is a cluster connected, and what
does it look like" for the portal's Cluster Connection UI. Any future
create/apply/delete test-execution logic belongs in tests/validation/, not
here, and must be explicit/opt-in per the product's security rules (no
kubeconfig upload, no credentials exposed to the browser, backend-only).

The browser never talks to this module directly -- only the FastAPI routers
do, over the portal's own REST API.
"""
from dataclasses import dataclass, field
from typing import Optional

from . import config


@dataclass
class ClusterInfo:
    connected: bool
    context: Optional[str] = None
    kubernetes_version: Optional[str] = None
    node_count: Optional[int] = None
    error: Optional[str] = None


def _kubeconfig_available() -> bool:
    import os

    if os.environ.get("KUBECONFIG"):
        return os.path.exists(os.environ["KUBECONFIG"])
    return os.path.exists(os.path.expanduser("~/.kube/config"))


def discover_cluster() -> ClusterInfo:
    """Best-effort, read-only cluster discovery. Never raises -- any failure
    (no kubeconfig, unreachable API, forbidden) is reported via
    ClusterInfo.connected=False plus .error, never as an exception the
    caller has to handle."""
    if config.IS_HOSTED:
        return ClusterInfo(connected=False, error="hosted mode never accesses a cluster")

    if not _kubeconfig_available():
        return ClusterInfo(connected=False, error="no kubeconfig found")

    try:
        from kubernetes import client, config as kube_config
    except ImportError:
        return ClusterInfo(connected=False, error="kubernetes python client not installed")

    try:
        kube_config.load_kube_config()
        contexts, active_context = kube_config.list_kube_config_contexts()
        context_name = active_context["name"] if active_context else None

        version_api = client.VersionApi()
        version_info = version_api.get_code()
        version_str = f"{version_info.major}.{version_info.minor} ({version_info.git_version})"

        core_v1 = client.CoreV1Api()
        nodes = core_v1.list_node()
        node_count = len(nodes.items)

        return ClusterInfo(
            connected=True,
            context=context_name,
            kubernetes_version=version_str,
            node_count=node_count,
        )
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: any cluster
        # access failure (auth, network, RBAC) degrades to "not connected",
        # it must never 500 the portal.
        return ClusterInfo(connected=False, error=str(exc))
