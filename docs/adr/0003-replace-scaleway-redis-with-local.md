# ADR 0003: Replace Scaleway Redis with Local Redis

## Status
Accepted

## Date
2026-02-10

## Context

The project uses Scaleway's managed Redis cluster as the Dapr pub/sub backend (`scaleway-redis-cluster-pubsub`). This requires:
- Scaleway account and billing
- Network access to Scaleway infrastructure
- Managing external service credentials

For self-hosted deployment on a home Tailnet, a local Redis instance is simpler and sufficient.

## Decision

Replace Scaleway Redis with a **local Redis container** running alongside the services. The Dapr pub/sub component will point to this local instance.

### Component configuration
`.dapr/components/redis-pubsub.yaml`

### Redis deployment
Will be added to the Podman compose stack in a later ADR.

## Consequences

### Positive
- No external service dependency
- No ongoing costs
- Lower latency (local network)
- Full control over the Redis instance

### Negative
- Must run Redis locally (minimal overhead)
- No managed backups (acceptable for this use case — pub/sub is ephemeral)

## Implementation

1. Create `.dapr/components/redis-pubsub.yaml`
2. Update pubsub name in both services from `scaleway-redis-cluster-pubsub` to `redis-pubsub`
