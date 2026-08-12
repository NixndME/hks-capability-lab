#!/usr/bin/env bash
# Build linux/amd64 + linux/arm64 for the GUIDED EXPERIENCE image (separate
# from the existing validator's docker.io/nixndme/hks-capability-lab --
# this is docker.io/nixndme/hks-capability-lab-experience). Same honesty
# rule as ../../scripts/build-multiarch.sh: never claims an architecture
# was built, or runtime-tested, if it wasn't.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."   # repo root (hks-experience/scripts/../..)

IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-docker.io/nixndme/hks-capability-lab-experience}"
TAG="${1:-dev}"
MANIFEST="${IMAGE_REPOSITORY}:${TAG}"
HOST_ARCH="$(podman info --format '{{.Host.Arch}}' 2>/dev/null || uname -m)"
CONTAINERFILE="hks-experience/Containerfile"

# Baked into the image as PUBLIC_GITHUB_OWNER/REPO/PUBLIC_ARTIFACT_REF (see
# Containerfile) so public YAML artifact URLs resolve at runtime -- this
# image never contains .git, so there's nothing to introspect once it's
# running. Derived from THIS checkout's own origin/branch, never hand-typed;
# override any of the three env vars before running this script if you're
# building from a fork or publishing a pinned release tag.
_origin_url="$(git remote get-url origin 2>/dev/null || true)"
_owner_repo="$(echo "$_origin_url" | sed -E 's#(git@github\.com:|https://github\.com/)([^/]+)/([^/.]+)(\.git)?#\2/\3#')"
PUBLIC_GITHUB_OWNER="${PUBLIC_GITHUB_OWNER:-${_owner_repo%%/*}}"
PUBLIC_GITHUB_REPO="${PUBLIC_GITHUB_REPO:-${_owner_repo##*/}}"
PUBLIC_ARTIFACT_REF="${PUBLIC_ARTIFACT_REF:-$(git branch --show-current 2>/dev/null || echo main)}"
echo "Public artifact URLs will resolve against: ${PUBLIC_GITHUB_OWNER}/${PUBLIC_GITHUB_REPO}@${PUBLIC_ARTIFACT_REF}"
BUILD_ARGS=(--build-arg "PUBLIC_GITHUB_OWNER=${PUBLIC_GITHUB_OWNER}" --build-arg "PUBLIC_GITHUB_REPO=${PUBLIC_GITHUB_REPO}" --build-arg "PUBLIC_ARTIFACT_REF=${PUBLIC_ARTIFACT_REF}")

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
  if podman build --platform "linux/${arch}" "${BUILD_ARGS[@]}" -t "${tag_local}" -f "${CONTAINERFILE}" . 2> "/tmp/hks-experience-build-${arch}.log"; then
    podman manifest add "${MANIFEST}" "containers-storage:${tag_local}" >/dev/null
    built_archs+=("${arch}")
    echo "Built linux/${arch} -> ${tag_local}"
  else
    skipped_archs+=("${arch}")
    echo "NOT EXECUTED: linux/${arch} build failed."
    if grep -qi "exec format error" "/tmp/hks-experience-build-${arch}.log"; then
      echo "  Reason: 'exec format error' -- no functional foreign-arch emulation in this"
      echo "  environment (confirmed even after host-level binfmt_misc QEMU registration --"
      echo "  see the existing validator's docker image build notes for the same finding)."
    fi
    tail -5 "/tmp/hks-experience-build-${arch}.log" | sed 's/^/  | /'
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
fi

echo
echo "Built: ${built_archs[*]:-none}"
echo "NOT EXECUTED (build failed / emulation unavailable): ${skipped_archs[*]:-none}"
for arch in "${built_archs[@]}"; do
  if [[ "${arch}" == "${HOST_ARCH}" ]]; then
    echo "Runtime-tested (this host is ${HOST_ARCH}): ${arch}"
  else
    echo "NOT RUNTIME-TESTED: linux/${arch} was built but never executed on this ${HOST_ARCH} host."
  fi
done

echo
echo "To push (only when you actually want to publish):"
echo "  podman manifest push --all ${MANIFEST} docker://${MANIFEST}"
