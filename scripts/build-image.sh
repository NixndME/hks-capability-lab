#!/usr/bin/env bash
# Build the portal container image with Podman, inspect it, and smoke-test
# its health endpoints. Single-architecture (host arch) build -- see
# build-multiarch.sh for the amd64+arm64 path.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-docker.io/nixndme/hks-capability-lab}"
TAG="${1:-dev}"
IMAGE="${IMAGE_REPOSITORY}:${TAG}"

if ! command -v podman >/dev/null 2>&1; then
  echo "podman not found -- this project builds with Podman, not Docker Desktop." >&2
  exit 1
fi

echo "== Podman version =="
podman --version

echo
echo "== Building ${IMAGE} =="
podman build -t "${IMAGE}" -f Containerfile .

echo
echo "== Image info =="
podman inspect "${IMAGE}" --format 'ID: {{.Id}}
Arch: {{.Os}}/{{.Architecture}}
Size: {{.Size}} bytes
Created: {{.Created}}'

echo
echo "== Smoke test =="
CONTAINER_NAME="hks-lab-build-smoke-$$"
PORT="${SMOKE_TEST_PORT:-18080}"
podman run -d --rm -p "${PORT}:8080" --name "${CONTAINER_NAME}" -e PORTAL_MODE=hosted "${IMAGE}" >/dev/null
cleanup() { podman stop "${CONTAINER_NAME}" >/dev/null 2>&1 || true; }
trap cleanup EXIT

for i in $(seq 1 20); do
  if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

echo -n "GET /health   -> "; curl -sf "http://127.0.0.1:${PORT}/health" && echo
echo -n "GET /ready    -> "; curl -sf "http://127.0.0.1:${PORT}/ready" && echo
echo -n "GET /api/info -> "; curl -sf "http://127.0.0.1:${PORT}/api/info" | head -c 200 && echo
echo -n "GET /         -> HTTP "; curl -s -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:${PORT}/"

echo
echo "Built and smoke-tested: ${IMAGE}"
