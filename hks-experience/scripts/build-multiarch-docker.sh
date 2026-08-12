#!/usr/bin/env bash
# Build + push linux/amd64 + linux/arm64 for the GUIDED EXPERIENCE image
# using Docker Buildx -- the recommended path for real multi-arch
# publishing. This project's original development host could only produce
# a working linux/amd64 build with rootless Podman (foreign-arch QEMU
# emulation didn't work there even with binfmt_misc registered at the host
# level -- see ../README.md and ../../scripts/build-multiarch.sh's own
# notes on the same finding). Docker Buildx's docker-container driver
# bundles its own QEMU emulation and is far more likely to "just work,"
# which is why this script exists as the primary way to publish arm64.
#
# Requires:
#   - Docker with the buildx plugin (`docker buildx version` should work;
#     install via your distro's docker-buildx-plugin / docker-ce package,
#     or use Docker Desktop, which bundles it)
#   - `docker login docker.io` already run (this script never touches
#     credentials itself)
#
# Usage:
#   ./build-multiarch-docker.sh              # build only (tag: latest), does not publish
#   ./build-multiarch-docker.sh 1.0.0 --push  # build AND push both architectures
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."   # repo root

IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-docker.io/nixndme/hks-capability-lab-experience}"
TAG="${1:-latest}"
PUSH=false
[[ "${2:-}" == "--push" ]] && PUSH=true
IMAGE="${IMAGE_REPOSITORY}:${TAG}"
CONTAINERFILE="hks-experience/Containerfile"
BUILDER_NAME="hks-experience-builder"
PLATFORMS="linux/amd64,linux/arm64"

echo "== Docker / Buildx version =="
docker --version
if ! docker buildx version >/dev/null 2>&1; then
  echo "docker buildx is not available. Install the buildx plugin (e.g." >&2
  echo "'docker-buildx-plugin' / 'docker-ce' package, or Docker Desktop) and re-run." >&2
  exit 1
fi
docker buildx version

# A plain default builder can't cross-build; create (or reuse) a
# docker-container builder, which bundles QEMU emulation for foreign
# architectures automatically -- no manual binfmt_misc registration step
# needed on most systems.
if ! docker buildx inspect "$BUILDER_NAME" >/dev/null 2>&1; then
  echo "Creating buildx builder '$BUILDER_NAME'..."
  docker buildx create --name "$BUILDER_NAME" --driver docker-container --use
else
  docker buildx use "$BUILDER_NAME"
fi
docker buildx inspect --bootstrap

echo
echo "== Building ${IMAGE} for ${PLATFORMS} =="

ARGS=(buildx build --platform "$PLATFORMS" -t "$IMAGE" -f "$CONTAINERFILE" .)
if [[ "$PUSH" == true ]]; then
  ARGS+=(--push)
else
  # A multi-platform build result can't be loaded into `docker images`
  # (only single-platform results can) -- without --push this only
  # exercises/validates the build, it produces nothing retrievable
  # afterward. Pass --push to actually publish both architectures.
  echo "NOTE: no --push passed -- this validates both platforms build"
  echo "successfully but does not publish anything. Re-run with --push to"
  echo "actually publish: $0 $TAG --push"
fi

docker "${ARGS[@]}"

if [[ "$PUSH" == true ]]; then
  echo
  echo "Pushed. Verify the manifest actually has both platforms:"
  echo "  docker buildx imagetools inspect ${IMAGE}"
fi
