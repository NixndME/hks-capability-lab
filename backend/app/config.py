"""Runtime configuration, sourced entirely from environment variables.

Nothing here hard-codes a domain into application *logic* -- these are
defaults only, consistent with the "no hard-coded domains" rule that also
applies to the Helm chart and manifests.
"""
import os

APP_NAME = "hks-capability-lab"
APP_DISPLAY_NAME = "HKS Capability Lab"

# PORTAL_MODE=hosted disables all kubeconfig/cluster access, unconditionally.
# Anything other than "hosted" (including unset) is treated as local mode,
# where cluster access is attempted but optional.
PORTAL_MODE = os.environ.get("PORTAL_MODE", "local").strip().lower()
IS_HOSTED = PORTAL_MODE == "hosted"

PUBLIC_BASE_URL = os.environ.get(
    "PUBLIC_BASE_URL",
    "https://hks.nixndme.com" if IS_HOSTED else "http://localhost:8080",
)
PORTAL_DOMAIN = os.environ.get("PORTAL_DOMAIN", "hks.nixndme.com")
API_BASE_URL = os.environ.get("API_BASE_URL", PUBLIC_BASE_URL)

# Default image repository, per the product brief -- configurable, never
# assumed to be pushed/available.
IMAGE_REPOSITORY = os.environ.get(
    "IMAGE_REPOSITORY", "docker.io/nixndme/hks-capability-lab"
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_DEFINITIONS_DIR = os.path.join(REPO_ROOT, "tests", "definitions")

APP_VERSION = os.environ.get("APP_BUILD_VERSION", "0.1.0-dev")
