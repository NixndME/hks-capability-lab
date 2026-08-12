"""Serves ../../../yaml/'s metadata + content to the frontend, and packages
the Helm chart for direct download -- the two ways this journey lets a
customer deploy without ever cloning the repository (see
../public_artifacts.py and ../../../yaml/README.md)."""
import glob
import logging
import os
import shutil
import subprocess

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from .. import config, public_artifacts

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public-yaml")


@router.get("")
def list_public_yaml():
    return {
        "raw_base_url": config.PUBLIC_GITHUB_RAW_BASE_URL or None,
        "repo_url": config.PUBLIC_GITHUB_REPO_URL or None,
        "owner": config.PUBLIC_GITHUB_OWNER or None,
        "repo": config.PUBLIC_GITHUB_REPO or None,
        "ref": config.PUBLIC_ARTIFACT_REF,
        "artifacts": [a.to_dict() for a in public_artifacts.list_all()],
    }


def _find_tgz(dir_path: str) -> str | None:
    files = glob.glob(os.path.join(dir_path, "*.tgz")) if os.path.isdir(dir_path) else []
    return files[0] if files else None


@router.get("/helm-chart.tgz")
def download_helm_chart():
    """Serves the Helm chart archive for direct download -- so a customer
    can `helm install` from one downloaded file without cloning the
    repository. Never a second copy of the chart itself (see
    ../../charts/README.md): this always packages
    ../../../helm/hks-capability-lab, the same chart the existing
    validator uses.

    Prefers a pre-built archive from config.HELM_CHART_DIST_DIR (the
    Containerfile runs `helm package` once at image build time -- see
    Containerfile) so this endpoint never depends on the `helm` binary or a
    subprocess call succeeding at request time in a running container.
    Falls back to live packaging for local dev (running uvicorn directly,
    outside the built image), and only then returns a clear error -- never
    a raw exception body masquerading as a .tgz download."""
    prebuilt = _find_tgz(config.HELM_CHART_DIST_DIR)
    if prebuilt:
        return FileResponse(prebuilt, media_type="application/gzip", filename=os.path.basename(prebuilt))

    chart_dir = os.path.join(config.REPO_ROOT, "helm", "hks-capability-lab")
    if not os.path.isdir(chart_dir):
        raise HTTPException(404, "Helm chart not found in this image")
    if not shutil.which("helm"):
        log.warning("Chart download requested but neither a pre-built archive (%s) nor the helm binary is available", config.HELM_CHART_DIST_DIR)
        raise HTTPException(503, "Chart download isn't available on this portal right now (no packaged chart and no helm binary) -- this is a portal deployment issue, not something you can fix as a user.")
    out_dir = "/tmp/hks-experience-helm-chart"
    os.makedirs(out_dir, exist_ok=True)
    for stale in glob.glob(os.path.join(out_dir, "*.tgz")):
        os.remove(stale)
    try:
        subprocess.run(
            ["helm", "package", chart_dir, "-d", out_dir],
            check=True, capture_output=True, timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("live helm package failed: %s", exc)
        raise HTTPException(503, "Chart packaging failed on this portal -- this is a portal deployment issue, not something you can fix as a user.") from exc
    tgz_path = _find_tgz(out_dir)
    if not tgz_path:
        raise HTTPException(503, "helm package produced no archive")
    return FileResponse(tgz_path, media_type="application/gzip", filename=os.path.basename(tgz_path))


@router.get("/{artifact_id}")
def get_public_yaml(artifact_id: str):
    artifact = public_artifacts.get(artifact_id)
    if not artifact:
        raise HTTPException(404, f"unknown artifact '{artifact_id}'")
    return artifact.to_dict()


@router.get("/{artifact_id}/raw", response_class=PlainTextResponse)
def get_public_yaml_raw(artifact_id: str):
    """Plain-text YAML content, byte-identical to the file's raw GitHub
    URL -- used by the frontend's Download button so it always saves under
    the artifact's real filename regardless of network access to GitHub."""
    artifact = public_artifacts.get(artifact_id)
    if not artifact:
        raise HTTPException(404, f"unknown artifact '{artifact_id}'")
    content = public_artifacts.read_yaml(artifact.filename)
    if content is None:
        raise HTTPException(404, f"{artifact.filename} not found on disk")
    return content
