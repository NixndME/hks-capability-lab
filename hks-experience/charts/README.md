# Helm charts

This journey drives the **same** Helm chart the existing validator already
has: [`../../helm/hks-capability-lab/`](../../helm/hks-capability-lab/).
Per the product brief's own instruction ("if the current repository already
has equivalent directories, adapt rather than duplicate"), this directory
doesn't re-package a second copy of that chart — duplicating ~500 lines of
already-validated Helm templates would create exactly the kind of drift
risk (two charts silently diverging) this project has been careful to
avoid elsewhere (see the `sync-helm-app-code.sh` discipline for the sample
app source).

The "Deploy with Helm" step in the journey (`workflows/deploy-app.yaml`)
points at `../../helm/hks-capability-lab` directly, and the backend's
artifact-bundle endpoint packages it live via `helm package` on demand.
