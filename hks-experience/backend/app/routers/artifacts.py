import glob
import io
import os
import subprocess
import zipfile

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from .. import config

router = APIRouter()


@router.get("/api/artifacts/bundle.zip")
def download_bundle():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        core = os.path.join(config.REPO_ROOT, "hks-capability-lab.yaml")
        if os.path.exists(core):
            zf.write(core, "yaml/hks-capability-lab.yaml")
        for path in glob.glob(os.path.join(config.REPO_ROOT, "manifests", "*.yaml")):
            zf.write(path, f"yaml/manifests/{os.path.basename(path)}")

        chart_dir = os.path.join(config.REPO_ROOT, "helm", "hks-capability-lab")
        if os.path.isdir(chart_dir):
            try:
                out_dir = "/tmp/hks-experience-helm-bundle"
                os.makedirs(out_dir, exist_ok=True)
                subprocess.run(
                    ["helm", "package", chart_dir, "-d", out_dir],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                for tgz in glob.glob(os.path.join(out_dir, "*.tgz")):
                    zf.write(tgz, f"helm/{os.path.basename(tgz)}")
            except Exception:  # noqa: BLE001
                # helm not available in this environment -- ship YAML only,
                # never fail the whole bundle over an optional piece.
                pass

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=hks-capability-lab-artifacts.zip"},
    )
