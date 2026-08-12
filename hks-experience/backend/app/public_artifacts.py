"""Metadata + content access for ../../yaml/ -- the customer-facing,
directly-downloadable Kubernetes manifests (separate from ../../manifests/,
which belongs to the existing CLI validator and uses envsubst templating
unsuitable for a customer to copy-paste). This module is read-only: it
never writes to yaml/, only reads what's already committed there and pairs
it with the metadata the guided-journey UI needs ("what does this create",
"why does it matter") without duplicating that prose into the workflow
YAML files too.

See ../../yaml/README.md for the human-readable version of this table.
"""
import os
from dataclasses import dataclass, field
from functools import lru_cache

from . import config


@dataclass
class Resource:
    kind: str
    name: str


@dataclass
class Artifact:
    id: str
    filename: str
    name: str
    description: str
    resources: list[Resource] = field(default_factory=list)

    def to_dict(self) -> dict:
        raw_url = config.public_yaml_url(self.filename)
        return {
            "id": self.id,
            "filename": self.filename,
            "name": self.name,
            "description": self.description,
            "resources": [{"kind": r.kind, "name": r.name} for r in self.resources],
            "raw_url": raw_url,
            "apply_command": f"kubectl apply -f {raw_url}" if raw_url else None,
            "content": read_yaml(self.filename),
        }


ARTIFACTS: list[Artifact] = [
    Artifact(
        "namespace", "01-namespace.yaml", "Create HKS Test Namespace",
        "Creates one isolated namespace (hks-capability-lab) that every later step lives in.",
        [Resource("Namespace", "hks-capability-lab")],
    ),
    Artifact(
        "application", "02-application.yaml", "Deploy HKS Demo Workload",
        "Deploys the sample application: its Deployment, internal Service, and the ConfigMap/Secret/RBAC it runs with.",
        [
            Resource("ConfigMap", "hks-lab-app-code"), Resource("Secret", "hks-lab-demo-secret"),
            Resource("ServiceAccount", "hks-lab-app"), Resource("Role", "hks-lab-app-readonly"),
            Resource("RoleBinding", "hks-lab-app-readonly"), Resource("Deployment", "hks-lab-app"),
            Resource("Service", "hks-lab-app"), Resource("PodDisruptionBudget", "hks-lab-app"),
        ],
    ),
    Artifact(
        "clusterip", "03-clusterip.yaml", "ClusterIP Service",
        "Creates internal-only access to the app, reachable by DNS name from inside the cluster.",
        [Resource("Service", "hks-lab-app")],
    ),
    Artifact(
        "nodeport", "04-nodeport.yaml", "NodePort Service",
        "Exposes the app on a fixed port across every worker node.",
        [Resource("Service", "hks-lab-app-nodeport")],
    ),
    Artifact(
        "loadbalancer", "05-loadbalancer.yaml", "LoadBalancer Service",
        "Requests a cloud/MetalLB-provisioned external IP for the app, if your cluster has that infrastructure.",
        [Resource("Service", "hks-lab-app-lb")],
    ),
    Artifact(
        "ingress", "06-ingress.yaml", "Ingress",
        "Routes HTTP traffic to the app by hostname through your cluster's existing Ingress controller.",
        [Resource("Ingress", "hks-lab-app")],
    ),
    Artifact(
        "gateway", "07-gateway.yaml", "Gateway API routing",
        "The Gateway API alternative to Ingress -- a Gateway plus an HTTPRoute to the app.",
        [Resource("Gateway", "hks-lab-gateway"), Resource("HTTPRoute", "hks-lab-app")],
    ),
    Artifact(
        "hpa", "08-hpa.yaml", "Horizontal Pod Autoscaler",
        "Automatically adjusts the app's replica count (2-6) based on CPU utilization.",
        [Resource("HorizontalPodAutoscaler", "hks-lab-app")],
    ),
    Artifact(
        "prometheus-rule", "09-prometheus.yaml", "Prometheus alert rule (optional)",
        "Adds an optional alert to your existing Prometheus/Alertmanager if the app's scrape target goes down.",
        [Resource("PrometheusRule", "hks-lab-app")],
    ),
    Artifact(
        "servicemonitor", "10-servicemonitor.yaml", "ServiceMonitor",
        "Wires the app into your cluster's existing Prometheus install via the Prometheus Operator.",
        [Resource("ServiceMonitor", "hks-lab-app")],
    ),
    Artifact(
        "storage", "11-storage.yaml", "Persistent Storage test",
        "Creates a PVC and a single-replica Deployment used to prove data survives pod replacement.",
        [Resource("PersistentVolumeClaim", "hks-lab-storage-test"), Resource("Deployment", "hks-lab-storage-test")],
    ),
    Artifact(
        "network-policy", "12-network-policy.yaml", "NetworkPolicy allow/deny test",
        "Creates 3 disposable pods and 2 NetworkPolicies proving permitted traffic works and unauthorized traffic is blocked.",
        [
            Resource("Deployment", "netpol-backend"), Resource("Service", "netpol-backend"),
            Resource("Deployment", "netpol-frontend"), Resource("Deployment", "netpol-untrusted"),
            Resource("NetworkPolicy", "netpol-default-deny-backend"), Resource("NetworkPolicy", "netpol-allow-frontend-to-backend"),
        ],
    ),
    Artifact(
        "rolling-update-v2", "13-rolling-update-v2.yaml", "Rolling Update -- v2",
        "Updates the app Deployment to APP_VERSION=v2, triggering a standard Kubernetes rolling update.",
        [Resource("Deployment", "hks-lab-app")],
    ),
    Artifact(
        "rolling-update-v3", "14-rolling-update-v3.yaml", "Rolling Update -- v3",
        "Updates the app Deployment to APP_VERSION=v3, triggering a second rolling update.",
        [Resource("Deployment", "hks-lab-app")],
    ),
    Artifact(
        "blue-green", "15-blue-green.yaml", "Blue/Green deployment",
        "Runs BLUE (v1) and GREEN (v2) side by side; a Service selector switches all traffic between them instantly.",
        [Resource("Deployment", "hks-lab-app-blue"), Resource("Deployment", "hks-lab-app-green"), Resource("Service", "hks-lab-bluegreen")],
    ),
    Artifact(
        "canary", "16-canary.yaml", "Canary deployment",
        "Sends ~10% of traffic to a new version via ingress-nginx's canary-weight annotation.",
        [Resource("Deployment", "hks-lab-app-canary"), Resource("Service", "hks-lab-app-canary"), Resource("Ingress", "hks-lab-app-canary")],
    ),
    Artifact(
        "resiliency", "17-resiliency.yaml", "PodDisruptionBudget",
        "The PodDisruptionBudget that protects the app from being fully drained during voluntary disruptions.",
        [Resource("PodDisruptionBudget", "hks-lab-app")],
    ),
]

_BY_FILENAME = {a.filename: a for a in ARTIFACTS}
_BY_ID = {a.id: a for a in ARTIFACTS}


@lru_cache(maxsize=32)
def read_yaml(filename: str) -> str | None:
    """Reads a yaml/ file's raw text -- the exact same bytes served at the
    file's raw GitHub URL, since both come from the same committed file.
    Used so Copy/Download/View YAML never need a live GitHub round-trip."""
    safe_name = os.path.basename(filename)  # defends against path traversal
    path = os.path.join(config.PUBLIC_YAML_DIR, safe_name)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def get_by_filename(filename: str) -> Artifact | None:
    return _BY_FILENAME.get(os.path.basename(filename))


def get(artifact_id: str) -> Artifact | None:
    return _BY_ID.get(artifact_id)


def list_all() -> list[Artifact]:
    return ARTIFACTS
