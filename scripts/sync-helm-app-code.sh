#!/usr/bin/env bash
# The Helm chart embeds the sample app source as a ConfigMap, same as
# hks-capability-lab.yaml does -- both need their own copy because Helm's
# .Files.Get is scoped to the chart directory and can't reach outside it.
# Run this after editing sample-app/app.py, before `helm package`/`helm
# template`, so the chart never silently drifts from the canonical source.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
cp sample-app/app.py helm/hks-capability-lab/files/app.py
echo "Synced sample-app/app.py -> helm/hks-capability-lab/files/app.py"
