# Artifacts

Raw YAML/evidence bundles are generated **live** by the backend
(`GET /api/artifacts/bundle.zip`) from the existing validator's own files —
[`../../hks-capability-lab.yaml`](../../hks-capability-lab.yaml),
[`../../manifests/`](../../manifests/), and the packaged Helm chart — not
duplicated as static copies here. Same reasoning as `../charts/README.md`:
one source of truth, zero drift risk.
