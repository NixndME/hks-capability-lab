import os
import subprocess

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

PUBLIC_YAML_DIR = os.path.join(REPO_ROOT, "yaml")


def _git(*args: str) -> str | None:
    """Best-effort `git` invocation against REPO_ROOT. Returns None on any
    failure (git missing, not a repo, no remote) -- callers must have a
    non-git fallback, since a built container image never ships `.git`
    (see hks-experience/.containerignore / Containerfile) and only has
    baked-in env vars to go on at runtime."""
    try:
        out = subprocess.run(
            ["git", "-C", REPO_ROOT, *args],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return out.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def _detect_github_owner_repo() -> tuple[str, str] | None:
    """Normalizes `git remote get-url origin` -- either SSH
    (git@github.com:OWNER/REPO.git) or HTTPS
    (https://github.com/OWNER/REPO.git) -- into (owner, repo)."""
    url = _git("remote", "get-url", "origin")
    if not url:
        return None
    url = url.strip().removesuffix(".git")
    if url.startswith("git@github.com:"):
        path = url.removeprefix("git@github.com:")
    elif "github.com/" in url:
        path = url.split("github.com/", 1)[1]
    else:
        return None
    parts = path.split("/")
    if len(parts) != 2 or not all(parts):
        return None
    return parts[0], parts[1]


# Owner/repo: explicit env vars take priority (this is what a built
# container image relies on -- baked in at build time via --build-arg, see
# scripts/build-multiarch*.sh -- since the image never contains `.git`);
# falls back to live git introspection, which only works when this is
# actually running inside a git checkout (local dev, or `uvicorn` run
# directly against the repo).
_owner_repo = _detect_github_owner_repo()
PUBLIC_GITHUB_OWNER = os.environ.get(
    "PUBLIC_GITHUB_OWNER", _owner_repo[0] if _owner_repo else ""
)
PUBLIC_GITHUB_REPO = os.environ.get(
    "PUBLIC_GITHUB_REPO", _owner_repo[1] if _owner_repo else ""
)

# The ref (branch or tag) public artifact URLs point at. Defaults to
# whatever branch this checkout is actually on; "main" if that can't be
# determined (e.g. no git). Production builds should pin this to a release
# tag (see yaml/README.md and hks-experience/README.md's "Versioning
# public artifacts" note) via PUBLIC_ARTIFACT_REF at build time.
PUBLIC_ARTIFACT_REF = os.environ.get(
    "PUBLIC_ARTIFACT_REF", _git("branch", "--show-current") or "main"
)

# Full override for the whole base URL, if someone wants to point at a
# fork, a mirror, or a different hosting entirely -- takes priority over
# owner/repo/ref above when set.
PUBLIC_GITHUB_RAW_BASE_URL = os.environ.get(
    "PUBLIC_GITHUB_RAW_BASE_URL",
    (
        f"https://raw.githubusercontent.com/{PUBLIC_GITHUB_OWNER}/{PUBLIC_GITHUB_REPO}/{PUBLIC_ARTIFACT_REF}/yaml"
        if PUBLIC_GITHUB_OWNER and PUBLIC_GITHUB_REPO
        else ""
    ),
)

# Not used for raw file URLs (GitHub doesn't require .git there), but handy
# for "view on GitHub" / repo links elsewhere in the UI.
PUBLIC_GITHUB_REPO_URL = (
    f"https://github.com/{PUBLIC_GITHUB_OWNER}/{PUBLIC_GITHUB_REPO}"
    if PUBLIC_GITHUB_OWNER and PUBLIC_GITHUB_REPO
    else ""
)


def public_yaml_url(filename: str) -> str | None:
    """Full raw GitHub URL for a file in yaml/, or None if the repository
    origin couldn't be determined (PUBLIC_GITHUB_RAW_BASE_URL unset and no
    git remote available) -- callers must handle that honestly (e.g. fall
    back to "Open Raw GitHub" being disabled with an explanation) rather
    than link to a URL that doesn't exist."""
    if not PUBLIC_GITHUB_RAW_BASE_URL:
        return None
    return f"{PUBLIC_GITHUB_RAW_BASE_URL}/{filename}"
