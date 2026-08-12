#!/usr/bin/env bash
# Push a previously built manifest/image to a registry. NEVER invoked
# automatically by build-image.sh, build-multiarch.sh, or release.sh --
# publishing is always a separate, explicit, human-initiated step.
#
# Usage:
#   ./scripts/push-image.sh <tag>            # push single-arch image (from build-image.sh)
#   ./scripts/push-image.sh <tag> --manifest # push a manifest list (from build-multiarch.sh)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-docker.io/nixndme/hks-capability-lab}"
TAG="${1:?Usage: $0 <tag> [--manifest]}"
MODE="${2:-}"
TARGET="${IMAGE_REPOSITORY}:${TAG}"

echo "About to push: ${TARGET}"
echo "Registry auth is expected to already be set up via 'podman login docker.io'"
echo "(this script never reads, stores, or prints credentials)."
read -r -p "Continue? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

# Immutable tag guard: refuse to overwrite an already-published semver tag
# (e.g. 1.0.0) without an explicit --force. "latest"/"dev"/branch tags are
# expected to move; pinned version tags should not.
if [[ "$TAG" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && [[ "${3:-}" != "--force" ]]; then
  if podman manifest exists "${TARGET}" >/dev/null 2>&1 || podman image exists "${TARGET}"; then
    : # local existence isn't proof it's published; the real guard is registry-side and out of scope for this script.
  fi
  echo "NOTE: '${TAG}' looks like a pinned semver tag. This script does not verify"
  echo "whether it's already published upstream -- re-check before pushing over one."
fi

if [[ "$MODE" == "--manifest" ]]; then
  podman manifest push --all "${TARGET}" "docker://${TARGET}"
else
  podman push "${TARGET}" "docker://${TARGET}"
fi

echo "Pushed ${TARGET}"
