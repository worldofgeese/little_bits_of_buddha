# ADR 0006: Add Podman Compose for Local Deployment

## Status
Accepted

## Date
2026-02-10

## Context

With Garden.io, Kubernetes, and cloud infrastructure removed, we need a local deployment solution. The target environment is rootless Podman on a home Tailnet.

Requirements:
- Run both microservices with Dapr sidecars
- Local Redis for pub/sub
- Compatible with existing OpenClaw Podman stack
- Simple to start/stop

## Decision

Add a `compose.yaml` for Podman Compose that defines:
- `redis` — Redis 7 Alpine for Dapr pub/sub
- `telegram-bot-service` — with Dapr sidecar
- `openai-service` — with Dapr sidecar
- `dapr-placement` — Dapr placement service for actor support (optional but good practice)

Dapr sidecars will be run using Dapr's multi-app run feature (`dapr run -f dapr.yaml`) for development, and as separate containers in production compose.

For simplicity in this first iteration, we'll use `dapr run -f` which handles sidecar injection automatically.

## Consequences

### Positive
- Single command to start the stack: `podman-compose up`
- Works with rootless Podman
- Can be extended to integrate with OpenClaw's existing compose

### Negative
- Dapr sidecar pattern in compose is more complex than `dapr run -f`
- For now, recommend `dapr run -f dapr.yaml` for local dev

## Implementation

1. Create `compose.yaml` with Redis service
2. Update `dapr.yaml` to work with local Redis
3. Document local run instructions in README
