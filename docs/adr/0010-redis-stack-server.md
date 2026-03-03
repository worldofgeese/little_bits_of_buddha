# ADR-0010: Redis Stack Server for Multi-Module Support

**Date:** 2026-03-03
**Status:** Accepted
**Deciders:** Tao Hansen, Kypris

## Context

Phase 1 requires Redis for multiple roles: state store (via Dapr), pub/sub (via Dapr), vector search (RediSearch), and rate limiting (redis-cell).

## Decision

Use `redis/redis-stack-server:latest` instead of `redis:7`.

## Rationale

Redis Stack Server bundles RediSearch, RedisJSON, RedisTimeSeries, and RedisBloom. This gives us:

- **RediSearch + RedisJSON**: Vector search over sutta embeddings stored as JSON documents.
- **redis-cell**: `CL.THROTTLE` command for precise per-user rate limiting. Falls back to `INCR + EXPIRE` if unavailable.
- **RedisTimeSeries**: Reserved for Phase 3 practice analytics.

## Consequences

- Image is larger than `redis:7` (~200MB vs ~50MB).
- All modules are available immediately without custom module loading.
- The statestore component (`.dapr/components/statestore.yaml`) must be copied into the Dapr sidecar image at build time.
