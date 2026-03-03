# ADR-0011: Trio Instead of Asyncio

**Date:** 2026-03-03
**Status:** Accepted (inherited)
**Deciders:** Tao Hansen (original), Kypris (documented)

## Context

The project uses trio as its async runtime instead of asyncio. This was an original design decision.

## Implications

- **DaprClient is sync-only.** All Dapr state store and pub/sub calls must be wrapped with `trio.to_thread.run_sync()`.
- **redis.asyncio works with trio** via anyio compatibility layer.
- **Hypercorn** is used as the ASGI server (supports trio natively). Uvicorn does not support trio.
- **triogram** (Telegram bot library) is trio-native.

## Consequences

- Every new Dapr integration point needs a sync wrapper function passed to `trio.to_thread.run_sync`.
- Phase 2 Dapr Actors will need the same wrapping pattern.
- Testing uses trio fixtures (`pytest-trio`), not `pytest-asyncio`.
