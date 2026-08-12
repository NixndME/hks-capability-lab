import os

APP_NAME = "hks-capability-lab-experience"
APP_DISPLAY_NAME = "HKS Capability Lab — Guided Experience"
APP_VERSION = os.environ.get("APP_BUILD_VERSION", "0.1.0-dev")

PORTAL_MODE = os.environ.get("PORTAL_MODE", "local").strip().lower()
IS_HOSTED = PORTAL_MODE == "hosted"

PUBLIC_BASE_URL = os.environ.get(
    "PUBLIC_BASE_URL",
    "https://hks.nixndme.com" if IS_HOSTED else "http://localhost:8080",
)
IMAGE_REPOSITORY = os.environ.get(
    "IMAGE_REPOSITORY", "docker.io/nixndme/hks-capability-lab-experience"
)

# hks-experience/backend/app/config.py -> repo root is 4 levels up
_HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIENCE_ROOT = os.path.dirname(os.path.dirname(_HERE))
REPO_ROOT = os.path.dirname(EXPERIENCE_ROOT)
WORKFLOWS_DIR = os.path.join(EXPERIENCE_ROOT, "workflows")
SHIM_SCRIPT = os.path.join(_HERE, "shim.sh")

# Execution is opt-in per action, explicitly enabled -- see README's
# "Live execution" note. Set EXPERIENCE_EXECUTION=disabled to force every
# action into reference-only mode (no subprocess/kubectl calls at all),
# e.g. for hosted deployments that should never touch a cluster.
EXECUTION_ENABLED = (
    not IS_HOSTED and os.environ.get("EXPERIENCE_EXECUTION", "enabled") != "disabled"
)

ACTION_TIMEOUT_SECONDS = int(os.environ.get("EXPERIENCE_ACTION_TIMEOUT", "200"))
