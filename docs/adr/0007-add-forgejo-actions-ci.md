# ADR 0007: Add Forgejo Actions CI/CD Workflow

## Status
Accepted

## Date
2026-02-10

## Context

With Garden.io removed, we need a CI/CD solution. Forgejo Actions is the native choice for our Forgejo instance on Paphos.

Requirements:
- Run tests on push/PR
- Use local Forgejo runner with Podman-in-Podman
- Leverage Devbox for reproducible environment
- Support `forgejo-runner exec --image -self-hosted` for local testing

## Decision

Add a Forgejo Actions workflow at `.forgejo/workflows/ci.yaml` that:
1. Checks out code
2. Sets up Devbox environment
3. Installs dependencies with PDM
4. Runs pytest

The workflow uses `-self-hosted` label to run on the local Forgejo runner.

## Consequences

### Positive
- Native integration with Forgejo
- Runs on local infrastructure (no cloud CI costs)
- Can test locally with `forgejo-runner exec`
- Uses same Devbox environment as development

### Negative
- Requires Forgejo runner to be running
- PINP setup needed for container builds

## Implementation

1. Create `.forgejo/workflows/ci.yaml`
2. Use `runs-on: -self-hosted` for local runner
3. Cache Devbox/Nix for faster builds
