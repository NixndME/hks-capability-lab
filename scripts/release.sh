#!/usr/bin/env bash
# Orchestrates the full release pipeline. Registry push is NEVER part of
# the default path -- pass --push explicitly, and even then push-image.sh
# asks for interactive confirmation.
#
# Usage:
#   ./scripts/release.sh --dry-run   # fast, non-mutating checks only
#   ./scripts/release.sh             # full pipeline: build + smoke test, no push
#   ./scripts/release.sh --push      # full pipeline, then prompt to push
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

DRY_RUN=false
DO_PUSH=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --push) DO_PUSH=true ;;
    *) echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

STEP=0
FAILED=()
pass() { STEP=$((STEP+1)); echo "[$STEP] PASS  $1"; }
fail() { STEP=$((STEP+1)); echo "[$STEP] FAIL  $1"; FAILED+=("$1"); }
skip() { STEP=$((STEP+1)); echo "[$STEP] SKIP  $1 -- $2"; }

echo "== HKS Capability Lab release pipeline =="
echo "Mode: $([ "$DRY_RUN" = true ] && echo 'dry-run (non-mutating checks only)' || echo 'full')"
echo

# 1. YAML validation -- every manifest + test definition parses.
if python3 -c "
import glob, sys, yaml
files = glob.glob('manifests/*.yaml') + ['hks-capability-lab.yaml'] + glob.glob('tests/definitions/*.yaml') + glob.glob('deploy/portal/*.yaml')
for f in files:
    try:
        list(yaml.safe_load_all(open(f)))
    except Exception as e:
        print(f'{f}: {e}', file=sys.stderr)
        sys.exit(1)
print(f'{len(files)} YAML files parsed OK')
"; then pass "YAML validation"; else fail "YAML validation"; fi

# 2. Helm lint / template / package (always safe, no cluster contact).
if command -v helm >/dev/null 2>&1; then
  if helm lint helm/hks-capability-lab >/tmp/release-helm-lint.log 2>&1 \
     && helm template hks-lab helm/hks-capability-lab >/dev/null 2>>/tmp/release-helm-lint.log \
     && for f in helm/examples/values-*.yaml; do helm template hks-lab helm/hks-capability-lab -f "$f" >/dev/null 2>>/tmp/release-helm-lint.log || exit 1; done; then
    pass "Helm lint + template (all example values)"
  else
    fail "Helm lint/template"; tail -10 /tmp/release-helm-lint.log
  fi
  if [[ "$DRY_RUN" == false ]]; then
    mkdir -p dist
    if helm package helm/hks-capability-lab -d dist >/tmp/release-helm-pkg.log 2>&1; then
      pass "Helm package -> $(ls dist/*.tgz | tail -1)"
    else
      fail "Helm package"
    fi
  else
    skip "Helm package" "dry-run"
  fi
else
  fail "helm not found on PATH"
fi

# 3. Frontend type-check (+ build, unless dry-run).
export PATH="$HOME/.local/opt/node-current/bin:$PATH"
if command -v npm >/dev/null 2>&1; then
  (cd frontend && npm run lint >/tmp/release-tsc.log 2>&1) && pass "Frontend type-check (tsc --noEmit)" || { fail "Frontend type-check"; tail -15 /tmp/release-tsc.log; }
  if [[ "$DRY_RUN" == false ]]; then
    (cd frontend && npm run build >/tmp/release-fe-build.log 2>&1) && pass "Frontend build (vite build)" || { fail "Frontend build"; tail -15 /tmp/release-fe-build.log; }
  else
    skip "Frontend build" "dry-run"
  fi
else
  fail "npm not found on PATH"
fi

# 4. Backend sanity check: definitions load, app imports.
if [[ -x backend/.venv/bin/python ]]; then
  PY=backend/.venv/bin/python
else
  PY=python3
fi
if (cd backend && "$OLDPWD/$PY" -c "
import sys; sys.path.insert(0, '.')
from app import definitions
d = definitions.load_all()
assert len(d) > 0
print(f'{len(d)} test definitions load OK')
" 2>/tmp/release-backend.log); then pass "Backend sanity check"; else fail "Backend sanity check"; cat /tmp/release-backend.log; fi

if [[ "$DRY_RUN" == true ]]; then
  echo
  echo "Dry-run complete. Full pipeline would also: build the container image"
  echo "(scripts/build-image.sh), run its smoke test, and optionally build"
  echo "linux/amd64+linux/arm64 (scripts/build-multiarch.sh) and push (--push)."
else
  # 5. Container build + smoke test.
  if bash scripts/build-image.sh release-candidate >/tmp/release-build.log 2>&1; then
    pass "Container build + smoke test"
  else
    fail "Container build + smoke test"; tail -20 /tmp/release-build.log
  fi

  if [[ "$DO_PUSH" == true ]]; then
    bash scripts/build-multiarch.sh release-candidate
    bash scripts/push-image.sh release-candidate --manifest
  fi
fi

echo
echo "== Summary =="
echo "${STEP} steps run, ${#FAILED[@]} failed."
if [[ ${#FAILED[@]} -gt 0 ]]; then
  printf 'FAILED: %s\n' "${FAILED[@]}"
  exit 1
fi
