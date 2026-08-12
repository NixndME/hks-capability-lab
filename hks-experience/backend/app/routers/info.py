from datetime import datetime, timezone

from fastapi import APIRouter

from .. import config, k8s

router = APIRouter()


@router.get("/api/info")
def api_info():
    cluster = k8s.discover_cluster()
    return {
        "application": config.APP_NAME,
        "display_name": config.APP_DISPLAY_NAME,
        "version": config.APP_VERSION,
        "mode": "hosted" if config.IS_HOSTED else "local",
        "execution_enabled": config.EXECUTION_ENABLED,
        "public_base_url": config.PUBLIC_BASE_URL,
        "image_repository": config.IMAGE_REPOSITORY,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kubernetes": {
            "connected": cluster.connected,
            "context": cluster.context,
            "version": cluster.version,
            "node_count": cluster.node_count,
            "error": cluster.error.to_dict() if cluster.error else None,
        },
    }
