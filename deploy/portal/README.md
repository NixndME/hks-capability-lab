# Portal deployment

Deploys **the portal itself** (frontend + backend, one container — see
`../../Containerfile`) into a Kubernetes cluster, e.g. to serve it at
`https://hks.nixndme.com`. Separate from `../../manifests/` and
`../../hks-capability-lab.yaml`, which deploy the *sample workload the
portal validates* into a customer's cluster.

```bash
cp portal.env.example portal.env   # edit PORTAL_DOMAIN, PORTAL_IMAGE, etc.
set -a && source portal.env && set +a
envsubst < portal.yaml | kubectl apply -f -
```

Always runs with `PORTAL_MODE=hosted` — this Deployment never mounts a
kubeconfig and the backend never attempts cluster access (see
`../../backend/app/k8s.py`); the pod requests no ServiceAccount permissions
beyond the default.

`PORTAL_IMAGE` must point at an image you've actually built and pushed
(see `../../scripts/build-multiarch.sh` and `../../scripts/push-image.sh`)
— nothing here builds or publishes the image itself.
