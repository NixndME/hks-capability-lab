#!/usr/bin/env bash
# Build linux/amd64 + linux/arm64 with Podman and assemble a manifest list.
#
# Honesty rule (see docs/INITIAL_ARCHITECTURE_ASSESSMENT.md): this script
# never claims an architecture was built if it wasn't, and never claims
# runtime testing happened on an architecture that was only cross-built.
# Foreign-arch builds require a working binfmt_misc QEMU registration on
# the HOST (not just inside a container's private mount namespace -- a
# `podman run --privileged tonistiigi/binfmt` only registers into its own
# container's namespace on kernels where binfmt_misc isn't shared with the
# host, which is common on rootless Podman setups without real root). If
# that's the situation here, the arm64 build is skipped and reported as
# NOT EXECUTED with the reason, rather than silently failing or faking it.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-docker.io/nixndme/hks-capability-lab}"
TAG="${1:-dev}"
MANIFEST="${IMAGE_REPOSITORY}:${TAG}"
HOST_ARCH="$(podman info --format '{{.Host.Arch}}' 2>/dev/null || uname -m)"

echo "== Podman version =="
podman --version
echo "Host architecture: ${HOST_ARCH}"
echo

built_archs=()
skipped_archs=()

podman manifest rm "${MANIFEST}" >/dev/null 2>&1 || true
podman manifest create "${MANIFEST}" >/dev/null

for arch in amd64 arm64; do
  echo "== linux/${arch} =="
  tag_local="${IMAGE_REPOSITORY}:${TAG}-${arch}"
  if podman build --platform "linux/${arch}" -t "${tag_local}" -f Containerfile . 2> "/tmp/build-${arch}.log"; then
    podman manifest add "${MANIFEST}" "containers-storage:${tag_local}" >/dev/null
    built_archs+=("${arch}")
    echo "Built linux/${arch} -> ${tag_local}"
  else
    skipped_archs+=("${arch}")
    echo "NOT EXECUTED: linux/${arch} build failed."
    if grep -qi "exec format error" "/tmp/build-${arch}.log"; then
      echo "  Reason: 'exec format error' during a RUN step -- no functional binfmt_misc"
      echo "  QEMU registration is available on the HOST for this architecture in this"
      echo "  environment (rootless Podman without host root cannot register one"
      echo "  persistently). See the tail of the build log below."
    fi
    tail -5 "/tmp/build-${arch}.log" | sed 's/^/  | /'
  fi
  echo
done

echo "== Manifest: ${MANIFEST} =="
if [[ ${#built_archs[@]} -gt 0 ]]; then
  podman manifest inspect "${MANIFEST}" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for m in data.get('manifests', []):
    p = m.get('platform', {})
    print(f\"  {p.get('os')}/{p.get('architecture')}\")
"
else
  echo "  (empty -- no architecture built successfully)"
fi

echo
echo "Built: ${built_archs[*]:-none}"
echo "NOT EXECUTED (build failed / emulation unavailable): ${skipped_archs[*]:-none}"
if [[ " ${built_archs[*]} " == *" ${HOST_ARCH} "* ]]; then
  echo "Runtime-tested (this host is ${HOST_ARCH}): ${HOST_ARCH} only -- see build-image.sh's smoke test."
fi
for arch in "${built_archs[@]}"; do
  if [[ "${arch}" != "${HOST_ARCH}" ]]; then
    echo "NOT RUNTIME-TESTED: linux/${arch} was built but never executed on this ${HOST_ARCH} host (no emulator available to run it)."
  fi
done

echo
echo "To push this manifest to a registry (only when you actually want to publish):"
echo "  podman manifest push --all ${MANIFEST} docker://${MANIFEST}"
