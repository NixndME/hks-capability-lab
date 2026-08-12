# Networking Decision

## Detected networking stack

- CNI: Calico (Tigera Operator v1.40.8), NetworkPolicy enforced.
- Ingress: community `ingress-nginx` v1.12.1, already installed in the
  `ingress-nginx` namespace, `IngressClass: nginx`. `Service` is type
  `LoadBalancer` but `EXTERNAL-IP` is permanently `<pending>` (NodePorts
  `31992`/`30337` work).
- Gateway API: standard `gateway.networking.k8s.io` CRDs are **not**
  installed. Calico's Tigera Operator *can* install and run a Gateway API
  implementation (CRD `gatewayapis.operator.tigera.io` is present) but no
  `GatewayAPI` custom resource has been created, so this capability is
  latent, not active.
- No MetalLB or cloud LB controller anywhere in the cluster.

## Recommended gateway/ingress for this lab

**Reuse the existing community ingress-nginx controller, accessed via
NodePort**, for all Ingress-based tests (canary weighting, host-based
routing, TLS).

## Reason

1. It is already running and healthy — installing anything else would be a
   second HTTP entry point on the same cluster, which the operating rules for
   this lab explicitly forbid ("do not install a second ingress/gateway
   solution merely because one exists already").
2. It already advertises working NodePorts, so it is immediately usable
   without any infrastructure change.
3. It supports everything this lab's tests need: host/path routing, TLS via
   Secret, and canary traffic splitting via
   `nginx.ingress.kubernetes.io/canary*` annotations (native, no service mesh
   required — satisfies the "no large service mesh" constraint in the spec).
4. Its `Service.type=LoadBalancer` never resolves (no LB implementation), so
   the only realistic entry points are NodePort and port-forward — both are
   fully exercised by `run-hks-test.sh`.

## Alternative (not enabled today)

Enable Calico's built-in Gateway API support by creating a `GatewayAPI`
custom resource (`operator.tigera.io/v1`). This would install the standard
Gateway API CRDs (`GatewayClass`, `Gateway`, `HTTPRoute`) cluster-wide and run
an Envoy-based data plane managed by the already-installed Tigera Operator.

This is the better long-term choice given the community ingress-nginx project
was retired upstream in March 2026 — but it is a **cluster-scoped change**
(new CRDs, new controller, affects how *any* future Ingress/Gateway workload
on this cluster could be routed) and is explicitly out of the "safe to do
automatically" category from the lab's operating rules. It was **not**
enabled during this run. If you want it enabled, say so explicitly and it
will be applied as an isolated follow-up with its own rollback plan (`kubectl
delete gatewayapi default` removes it cleanly, since Tigera manages it as one
owned resource).

## Required prerequisites

None beyond what already exists — no new components are installed for the
default path (Ingress via existing controller, reached over NodePort).

## Risks

- **Ingress NGINX is a retired upstream project** (as of March 2026). It
  still functions correctly in this lab and receives no further evaluation
  here beyond "does it route traffic correctly" — it is not being newly
  adopted, only reused for testing purposes. Do not treat its presence here
  as an endorsement for new production use.
- NodePort access is tied to node IPs (`192.168.122.230-233`), which are
  private (RFC1918 / libvirt NAT range). There is no publicly routable
  address anywhere on this cluster today — see the "Public vs private
  access" section of `run-hks-test.sh` output and `TEST_RESULTS.md` for how
  this is handled.

## How to remove it

Nothing new is installed by this decision — there is nothing to roll back.
If the Gateway API alternative is enabled later: `kubectl delete gatewayapi
default` (Tigera Operator tears down the CRDs/controller it created).

## Domain / DNS

Since there is no publicly routable address, `TEST_HOST` from
`config.env` will be resolved either via NodePort + `/etc/hosts` style
`curl --resolve`/`Host:` header testing, or via port-forward for local-only
access. There is no DNS record to publish externally from this environment;
`run-hks-test.sh` documents this per access method rather than assuming a
real DNS record exists.
