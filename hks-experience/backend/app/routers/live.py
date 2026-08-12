"""Read-only live polling endpoints backing the frontend's flagship
visualizations (HPA replica count, blue/green traffic track, deployment
rollout state). Never mutates -- same discipline as k8s.py."""
from fastapi import APIRouter

router = APIRouter()

NAMESPACE = "hks-capability-lab"


def _client():
    from kubernetes import client, config as kube_config

    kube_config.load_kube_config()
    return client


@router.get("/api/live/hpa")
def live_hpa():
    try:
        client = _client()
        auto = client.AutoscalingV2Api()
        hpa = auto.read_namespaced_horizontal_pod_autoscaler("hks-lab-app", NAMESPACE)
        current_cpu = None
        if hpa.status.current_metrics:
            for m in hpa.status.current_metrics:
                if m.resource and m.resource.name == "cpu":
                    current_cpu = m.resource.current.average_utilization
        return {
            "connected": True,
            "replicas": hpa.status.current_replicas,
            "min_replicas": hpa.spec.min_replicas,
            "max_replicas": hpa.spec.max_replicas,
            "target_cpu": hpa.spec.metrics[0].resource.target.average_utilization if hpa.spec.metrics else None,
            "current_cpu": current_cpu,
        }
    except Exception as exc:  # noqa: BLE001
        return {"connected": False, "error": str(exc)}


@router.get("/api/live/deployment")
def live_deployment():
    try:
        client = _client()
        apps = client.AppsV1Api()
        dep = apps.read_namespaced_deployment("hks-lab-app", NAMESPACE)
        return {
            "connected": True,
            "ready_replicas": dep.status.ready_replicas or 0,
            "updated_replicas": dep.status.updated_replicas or 0,
            "replicas": dep.status.replicas or 0,
            "version": next(
                (e.value for e in dep.spec.template.spec.containers[0].env if e.name == "APP_VERSION"), None
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {"connected": False, "error": str(exc)}


@router.get("/api/live/bluegreen")
def live_bluegreen():
    try:
        client = _client()
        core = client.CoreV1Api()
        svc = core.read_namespaced_service("hks-lab-bluegreen", NAMESPACE)
        track = (svc.spec.selector or {}).get("hks-capability-lab/track")
        return {"connected": True, "active_track": track}
    except Exception as exc:  # noqa: BLE001
        return {"connected": False, "error": str(exc)}
