"""Serves ../../../yaml/'s metadata + content to the frontend, and packages
the Helm chart for direct download -- the two ways this journey lets a
customer deploy without ever cloning the repository (see
../public_artifacts.py and ../../../yaml/README.md)."""
import glob
import os
import subprocess

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from .. import config, public_artifacts

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


@router.get("/helm-chart.tgz")
def download_helm_chart():
    """Packages ../../../helm/hks-capability-lab live via `helm package` --
    the same chart the existing validator uses, never a second copy (see
    ../../charts/README.md) -- so a customer can `helm install` from a
    single downloaded archive without cloning the repository."""
    chart_dir = os.path.join(config.REPO_ROOT, "helm", "hks-capability-lab")
    if not os.path.isdir(chart_dir):
        raise HTTPException(404, "Helm chart not found in this image")
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
        raise HTTPException(503, f"helm package failed: {exc}") from exc
    tgz_files = glob.glob(os.path.join(out_dir, "*.tgz"))
    if not tgz_files:
        raise HTTPException(503, "helm package produced no archive")
    tgz_path = tgz_files[0]
    filename = os.path.basename(tgz_path)

    def stream():
        with open(tgz_path, "rb") as f:
            yield from f

    return StreamingResponse(
        stream(),
        media_type="application/gzip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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
