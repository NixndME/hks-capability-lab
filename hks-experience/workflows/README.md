# Workflow definitions

The guided journey's content — 23 steps across 10 categories, one YAML file
per category (a list of steps each). This is the source of truth the
frontend renders from and the backend's executor keys off of; nothing here
duplicates `../../tests/definitions/` — instead each step optionally sets
`test_ref` pointing at the underlying capability ID(s) there for
traceability back to the already-validated evidence.

## Schema

```yaml
id: string                 # stable step id, used in URLs and progress state
category: string            # sidebar grouping
order: number                # position within the overall journey
title: string
skippable: bool               # false only for Getting Started steps
prerequisites: [string]        # informational only -- the step ids this one is WRITTEN to
                                 # assume (e.g. its manifest references a namespace/Service
                                 # created earlier). Never enforced: every step is directly
                                 # reachable from the sidebar/URL regardless of what else is
                                 # COMPLETED/SKIPPED, so a customer can jump straight to e.g.
                                 # Helm or Scaling. If a step's action genuinely depends on
                                 # cluster state that isn't there yet, that surfaces honestly
                                 # as this step's own BLOCKED/FAILED result, not a lock.
test_ref: [string]              # optional cross-refs into tests/definitions/*.yaml ids
what: string                     # "What are we testing?"
why: string                       # "Why does this matter?"
what_you_will_do: [string]         # numbered mini-plan shown before the action
deploy:                             # omitted for pure-observation/discovery/DNS steps
  yaml:
    artifact: string                  # a ../../yaml/ public_artifacts id (e.g. "namespace"),
                                        # NOT a filename -- hydrated live against ../../yaml/
                                        # by backend/app/workflow.py's _hydrate_yaml_deploy,
                                        # which is where filename/description/resources/
                                        # raw_url/apply_command/content all come from. Never
                                        # duplicate that metadata by hand here.
    commands: [string]                  # OPTIONAL: extra kubectl-only follow-up commands
                                          # beyond the apply itself (rollout status, a
                                          # discovery lookup) -- never envsubst/kubectl-create
                                          # pipelines; the apply command itself is always
                                          # auto-derived from the artifact's raw GitHub URL.
  helm: {chart: string, commands: [string]}   # omitted if this step has no Helm path
manual_commands: [string]            # OPTIONAL: plain kubectl commands for steps with no
                                       # deployable manifest at all (port-forward, rollback,
                                       # a blue/green traffic-switch patch) -- shown in a
                                       # "Run this" block even though deploy.yaml is absent.
verify:
  description: string
  success_conditions: [string]
  executor: string|null              # key into backend/app/executor.py's ACTIONS map, or null
                                       # (null = user self-confirms after running the copied command)
expected_result: string
learn_more: string                    # optional "why did X happen" explainer template;
                                        # rendered only when the actual observed result supports it
```

## Steps (23) by category

1. **Getting Started** — cluster-prep, namespace, deploy-app
2. **Application Access** — open-app, clusterip, port-forward, nodeport, loadbalancer, ingress-gateway, domain
3. **Scaling** — hpa, cpu-load, memory-load
4. **Observability** — prometheus
5. **Lifecycle** — rolling-update, rollback, blue-green, canary
6. **Storage** — storage
7. **Security** — network-policy
8. **Scheduling** — scheduling
9. **Resiliency** — resiliency
10. **Autoscaling** — cluster-autoscaler

All 23 steps drive the **same** `hks-capability-lab` namespace/resources the
existing validator (`../../run-hks-test.sh`) already manages — this journey
is a different way to *operate* that proven engine, not a second copy of
it.
