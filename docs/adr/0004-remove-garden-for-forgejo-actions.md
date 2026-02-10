# ADR 0004: Remove Garden.io in Favor of Forgejo Actions

## Status
Accepted

## Date
2026-02-10

## Context

The project uses Garden.io for:
- Kubernetes deployment orchestration
- Development workflow automation
- CI/CD pipelines

Garden.io adds complexity:
- Requires Garden CLI installation
- Tightly coupled to Kubernetes
- Overkill for a two-service application on local Podman

For self-hosted deployment on a home Tailnet using rootless Podman, Forgejo Actions provides a simpler CI/CD solution that:
- Integrates natively with Forgejo
- Runs locally via `forgejo-runner`
- Uses standard container workflows

## Decision

Remove all Garden.io configuration and replace with Forgejo Actions (in a subsequent commit).

### Files to remove
- `project.garden.yml`
- `actions.garden.yml`
- `workflows.garden.yml`
- `.garden/` directory

### Files to add (next commit)
- `.forgejo/workflows/` with CI/CD workflow definitions

## Consequences

### Positive
- Simpler toolchain
- Native integration with Forgejo
- Can test locally with `forgejo-runner exec`
- No external CLI dependencies beyond Forgejo runner

### Negative
- Lose Garden's dev-loop features (acceptable — not needed for this project)

## Implementation

1. Delete Garden configuration files
2. Update .gitignore to remove Garden references
3. Add Forgejo Actions workflows (next ADR)
