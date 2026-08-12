"""Read-only cluster status + capability discovery, using the Kubernetes
PYTHON CLIENT directly (not kubectl) -- this app never requires kubectl to
exist just to answer "can we connect and what does this cluster have".
kubectl is only used by shim.sh for the mutating actions (deploy, apply,
etc.) that legitimately need the existing validator's render_apply/envsubst
machinery.

Separates two different questions, on purpose (see the product's own
"Cluster Preparation must not fail because of optional infrastructure"
requirement):
  1. Can we connect to Kubernetes at all? (discover_cluster)
  2. What optional capabilities does it have? (discover_capabilities --
     each one is independently "detected" / "not_detected" / "unknown",
     never a failure of the overall check)
"""
from dataclasses import dataclass, field

from . import config, errors

NAMESPACE = "hks-capability-lab"


@dataclass
class ClusterStatus:
    connected: bool
    context: str | None = None
    version: str | None = None
    node_count: int | None = None
    error: errors.StructuredError | None = None


@dataclass
class Capabilities:
    cni: str = "unknown"
    storage: str = "unknown"
    prometheus: str = "unknown"
    ingress: str = "unknown"
    gateway_api: str = "unknown"
    cluster_autoscaler: str = "unknown"
    notes: dict = field(default_factory=dict)


def _load_client():
    """Loads kube config and returns the `kubernetes.client` module, or
    raises a classified exception. Isolated so both discover_cluster and
    discover_capabilities share identical, tested error handling."""
    from kubernetes import client, config as kube_config

    kube_config.load_kube_config()
    return client


def discover_cluster() -> ClusterStatus:
    if config.IS_HOSTED:
        # Explicit mode decision, not an incidental failure: hosted mode
        # never even attempts to load a kubeconfig, guaranteed, regardless
        # of whether one happens to be present in this environment.
        return ClusterStatus(connected=False, error=errors.build("HOSTED_MODE_NOT_EXECUTED"))
    try:
        from kubernetes import client as _client_mod  # noqa: F401
    except ImportError as exc:
        return ClusterStatus(connected=False, error=errors.build("INTERNAL_ERROR", str(exc)))

    try:
        from kubernetes import config as kube_config

        client = _load_client()
        _, active = kube_config.list_kube_config_contexts()
        version_api = client.VersionApi()
        v = version_api.get_code(_request_timeout=8)
        core = client.CoreV1Api()
        nodes = core.list_node(_request_timeout=8)
        return ClusterStatus(
            connected=True,
            context=active["name"] if active else None,
            version=f"{v.major}.{v.minor} ({v.git_version})",
            node_count=len(nodes.items),
        )
    except Exception as exc:  # noqa: BLE001
        return ClusterStatus(connected=False, error=errors.classify_exception(exc))


def discover_capabilities() -> Capabilities:
    """Best-effort, independent per-capability discovery. A failure probing
    ONE capability never affects the others -- each is reported on its own,
    per the "optional infrastructure absence is not an error" rule."""
    caps = Capabilities()
    if config.IS_HOSTED:
        caps.notes["error"] = errors.build("HOSTED_MODE_NOT_EXECUTED").to_dict()
        return caps
    try:
        client = _load_client()
    except Exception as exc:  # noqa: BLE001
        caps.notes["error"] = errors.classify_exception(exc).to_dict()
        return caps

    # CNI: not exposed directly by the API -- heuristic from known
    # DaemonSet names, same class of detection the existing validator's
    # scripts/lib.sh does for other capabilities (real, just pattern-based,
    # not fabricated). Checked cluster-wide, not just kube-system: e.g. a
    # Tigera Calico install runs its DaemonSet in its own "calico-system"
    # namespace, not kube-system.
    try:
        apps = client.AppsV1Api()
        ds_names = {d.metadata.name for d in apps.list_daemon_set_for_all_namespaces(_request_timeout=8).items}
        for name, label in (("calico-node", "Calico"), ("cilium", "Cilium"), ("kube-flannel-ds", "Flannel"), ("weave-net", "Weave")):
            if any(name in n for n in ds_names):
                caps.cni = label
                break
        else:
            caps.cni = "unknown"
    except Exception as exc:  # noqa: BLE001
        caps.cni = "unknown"
        caps.notes["cni_error"] = str(exc)[:200]

    # Storage: any StorageClass present; Rook/Ceph specifically if named.
    try:
        core = client.CoreV1Api()
        storage = client.StorageV1Api()
        scs = storage.list_storage_class(_request_timeout=8).items
        if any("rook" in (sc.provisioner or "") or "ceph" in (sc.provisioner or "") for sc in scs):
            caps.storage = "Rook/Ceph"
        elif scs:
            caps.storage = "detected"
        else:
            caps.storage = "not_detected"
        _ = core
    except Exception as exc:  # noqa: BLE001
        caps.storage = "unknown"
        caps.notes["storage_error"] = str(exc)[:200]

    # Prometheus Operator: ServiceMonitor CRD present.
    try:
        ext = client.ApiextensionsV1Api()
        crds = {c.metadata.name for c in ext.list_custom_resource_definition(_request_timeout=8).items}
        caps.prometheus = "detected" if "servicemonitors.monitoring.coreos.com" in crds else "not_detected"
        caps.gateway_api = "detected" if "gateways.gateway.networking.k8s.io" in crds else "not_detected"
    except Exception as exc:  # noqa: BLE001
        caps.prometheus = "unknown"
        caps.gateway_api = "unknown"
        caps.notes["crd_error"] = str(exc)[:200]

    # Ingress controller: any IngressClass registered.
    try:
        net = client.NetworkingV1Api()
        classes = net.list_ingress_class(_request_timeout=8).items
        caps.ingress = classes[0].metadata.name if classes else "not_detected"
    except Exception as exc:  # noqa: BLE001
        caps.ingress = "unknown"
        caps.notes["ingress_error"] = str(exc)[:200]

    # Cluster Autoscaler: pod name heuristic across namespaces.
    try:
        core = client.CoreV1Api()
        pods = core.list_pod_for_all_namespaces(_request_timeout=8).items
        caps.cluster_autoscaler = "detected" if any("cluster-autoscaler" in (p.metadata.name or "") for p in pods) else "not_detected"
    except Exception as exc:  # noqa: BLE001
        caps.cluster_autoscaler = "unknown"
        caps.notes["autoscaler_error"] = str(exc)[:200]

    return caps


def reconcile_step(step_id: str) -> str | None:
    """Returns COMPLETED/None based on real cluster state for the handful of
    steps we can check cheaply and unambiguously; None means "no opinion,
    trust client state" (used for everything without an obvious single
    resource to check)."""
    if config.IS_HOSTED:
        return None
    try:
        client = _load_client()
        core = client.CoreV1Api()
        apps = client.AppsV1Api()
        autoscaling = client.AutoscalingV2Api()

        if step_id == "namespace":
            ns = core.read_namespace(NAMESPACE, _request_timeout=5)
            return "COMPLETED" if ns.status.phase == "Active" else None
        if step_id == "deploy-app":
            dep = apps.read_namespaced_deployment("hks-lab-app", NAMESPACE, _request_timeout=5)
            ready = dep.status.ready_replicas or 0
            desired = dep.spec.replicas or 1
            return "COMPLETED" if ready >= desired else None
        if step_id == "hpa":
            autoscaling.read_namespaced_horizontal_pod_autoscaler("hks-lab-app", NAMESPACE, _request_timeout=5)
            return "COMPLETED"
    except Exception:  # noqa: BLE001
        return None
    return None
