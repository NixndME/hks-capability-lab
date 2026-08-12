# Test Definitions

This directory is the **single source of truth** for every capability the
HKS Capability Lab knows how to validate. The portal UI, the CLI
(`run-hks-test.sh`), the report generator, and the capability matrix are all
expected to read from these files rather than hard-coding test knowledge
independently (see `docs/INITIAL_ARCHITECTURE_ASSESSMENT.md`).

One YAML file per category, each containing a list of test definitions.
Every definition here was transcribed from the already-validated results in
`../../TEST_RESULTS.md` and `../../HKS_CAPABILITY_MATRIX.md` — nothing was
invented. Where the prior run recorded `NOT AVAILABLE` or `NOT VALIDATED`,
that's preserved verbatim rather than upgraded to a PASS.

## Schema

```yaml
id: string              # stable ID, e.g. NET-003 (matches docs/validation/TEST_RESULTS.md where one exists)
name: string             # short human-readable name
category: string         # Networking | Storage | Observability | Scaling |
                          # Deployments | Security | Scheduling | Resiliency | Application
description: string      # what this test validates and why
purpose: string           # optional, one-line "why this matters" for the wizard UI
prerequisites: [string]   # other test IDs that must pass/exist first
deployment_modes: [string] # which of [yaml, helm] can currently exercise this.
                            # "helm" only appears once helm/hks-capability-lab/
                            # actually exists and covers it (phase 4) -- do not
                            # add it speculatively.
artifacts: [string]       # existing repo-relative manifest/script paths that implement the test
commands: [string]        # representative kubectl/curl commands a user/portal runs
success_conditions: [string] # machine-checkable conditions that define a PASS
result: string            # PASS | FAIL | NOT_AVAILABLE | NOT_VALIDATED | NOT_APPLICABLE | BLOCKED | NOT_TESTED
result_notes: string       # why, especially for anything not PASS -- see semantics below
evidence: [string]         # repo-relative evidence/ paths backing the result
docs: [string]              # related top-level markdown writeups
last_validated: string       # ISO date of the run the result field reflects
```

## Result semantics (must not be collapsed into pass/fail)

Per the product brief, these are deliberately distinct:

- `PASS` — end-to-end validated against a live cluster, evidence exists.
- `FAIL` — executed, did not behave as expected.
- `NOT_AVAILABLE` — the Kubernetes API supports the capability, but the
  infrastructure/implementation needed for it does not exist on the tested
  cluster (e.g. Cluster Autoscaler: no node-pool integration).
- `NOT_VALIDATED` — capability may exist (API and/or infra) but was not
  exercised end-to-end (e.g. Gateway API: enabling it is cluster-scoped and
  wasn't done; PodMonitor: CRD present, not exercised).
- `NOT_APPLICABLE` — doesn't apply in the current context.
- `BLOCKED` — a prerequisite failed or is missing.
- `NOT_TESTED` — defined but not yet run in this environment.

A report or UI must never present `NOT_AVAILABLE`/`NOT_VALIDATED` as a
failure — they are gaps in infrastructure or scope, not defects.
