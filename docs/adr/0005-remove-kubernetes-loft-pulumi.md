# ADR 0005: Remove Kubernetes, Loft, and Pulumi/Terraform

## Status
Accepted

## Date
2026-02-10

## Context

The project includes infrastructure-as-code and Kubernetes configurations:
- `terraform/` — Pulumi configuration for Loft and Kubernetes
- `my-chart/` — Helm chart for Kubernetes deployment

These were designed for cloud Kubernetes deployments with:
- Loft for namespace management
- Scaleway as cloud provider
- Complex RBAC and secret management

For self-hosted deployment on a home Tailnet using rootless Podman, these are unnecessary overhead.

## Decision

Remove all Kubernetes, Loft, and Pulumi/Terraform configurations. Deployment will use Podman Compose instead (defined in a later ADR).

### Files to remove
- `terraform/` directory
- `my-chart/` directory

## Consequences

### Positive
- Dramatically simpler deployment
- No Kubernetes knowledge required
- No cloud provider dependencies
- Faster iteration

### Negative
- Lose Kubernetes scalability (not needed for this use case)
- Example of K8s deployment removed (can be documented if needed later)

## Implementation

1. Delete `terraform/` directory
2. Delete `my-chart/` directory
3. Update .gitignore to remove related entries
