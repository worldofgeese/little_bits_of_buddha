# VISION.md — Little Bits of Buddha

## What

A Telegram bot that speaks as the Buddha, responding to users with teachings from the Early Buddhist Canon. Uses RAG over the Sutta Piṭaka, meditation workflows via Dapr, seeker state tracking (practice levels), and tool-calling for interactive experiences.

## Stack

- **Runtime:** Python 3.12+ with trio async
- **Services:** 5 microservices communicating via Dapr pub/sub over Redis
  - `telegram_bot_service` — Telegram API interface (triogram/trio)
  - `wisdom_service` — Core wisdom endpoint (Starlette/FastAPI, RAG, Anthropic proxy)
  - `openai_service` — LLM routing via LiteLLM
  - `seeker_actor_service` — Per-user state tracking via Dapr actors
  - `meditation_workflow_service` — Guided meditation via Dapr workflows
- **LLM:** Anthropic Claude (via Bedrock proxy)
- **Search:** Redis with RediSearch (vector + BM25 for sutta retrieval)
- **Orchestration:** Dapr (pub/sub, actors, workflows, state store)
- **CI:** Forgejo Actions (scripts-only pattern)
- **Container:** Docker Compose with Dapr sidecars

## Current State (2026-03-11)

All CI green. Tests: 219 passing (unit), 10 integration (deselected, require Dapr runtime). Lint clean (ruff + ty). Container builds passing.

## Key Design Decisions

- Trio over asyncio (existing codebase choice, deeply embedded)
- Dapr for all service-to-service communication (no direct HTTP between services)
- ty.toml downgrades `unresolved-import` and `invalid-argument-type` to warn (dapr-ext-workflow stubs don't resolve in CI lint env)
- Scripts-only CI (no actions/*, no Node.js deps)
- CI preflight script checks for required deps before running tests/lint
