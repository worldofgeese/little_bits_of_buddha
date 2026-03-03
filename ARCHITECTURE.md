# Architecture

## Overview

Little Bits of Buddha is a Telegram chatbot that teaches the Dhamma using an LLM augmented with semantic sutta search and conversation memory. It uses a microservices architecture orchestrated by [Dapr](https://dapr.io/) with Redis as the backing store for state, pub/sub, and vector search.

## Why Microservices?

This architecture isn't arbitrary. Each component handles a distinct concern that benefits from isolation:

- **Telegram service**: Stateless webhook handler. Receives messages, publishes to Dapr pub/sub, subscribes to responses. Restarts don't lose state.
- **OpenAI service** (wisdom service): RAG pipeline + LLM calls. CPU-intensive embedding + network-bound LLM calls. Independent scaling and failure isolation from the bot.
- **Redis**: State store (conversation history), vector search (sutta embeddings), rate limiting (per-user), pub/sub (message routing). One process, multiple roles — all Redis modules.
- **Dapr sidecars**: Service mesh. Handles pub/sub, state store access, and eventual actor/workflow lifecycle. Decouples application code from infrastructure.

## Container Topology

```
┌─────────────────────────────────────────────────────────────────┐
│  Podman Network: lbob_default                                   │
│                                                                 │
│  ┌──────────────┐   ┌───────────────┐   ┌───────────────────┐  │
│  │ lbob-telegram │   │ lbob-openai   │   │ lbob-redis        │  │
│  │ (triogram)    │   │ (trio+fastapi)│   │ (redis-stack)     │  │
│  │ port 8080     │   │ port 8080     │   │ port 6379         │  │
│  └──────┬───────┘   └──────┬───────┘   │ • state store      │  │
│         │ network_mode:     │ network_   │ • vector search    │  │
│         │ shares namespace  │ shares ns  │ • pub/sub          │  │
│  ┌──────┴───────┐   ┌──────┴───────┐   │ • rate limiting    │  │
│  │ lbob-telegram│   │ lbob-openai  │   └───────────────────┘  │
│  │ -dapr        │   │ -dapr        │                           │
│  │ port 3500    │   │ port 3500    │   ┌───────────────────┐  │
│  └──────────────┘   └──────────────┘   │ lbob-placement    │  │
│                                         │ (Dapr placement)  │  │
│                                         │ port 50005        │  │
│                                         └───────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Critical: Container Network Sharing

Dapr sidecars use `network_mode: "service:<app>"` (Podman) / `network_mode: "container:<app>"` (Docker). This means the sidecar **joins the app container's network namespace**. Both share `localhost`.

**Restart order matters:**
1. Stop both: `docker stop lbob-openai-dapr lbob-openai`
2. Start app first: `docker start lbob-openai`
3. Start sidecar second: `docker start lbob-openai-dapr`

Reversing this or restarting individually breaks the shared namespace. The sidecar will fail to bind to port 3500 if the app container it depends on isn't running.

## Message Flow

```
User sends Telegram message
  → Telegram Bot API webhook
    → lbob-telegram receives message
      → Dapr pub/sub publish to "messages" topic (via sidecar, port 3500)
        → Redis pub/sub routes to openai-service subscriber
          → lbob-openai receives CloudEvent
            → Rate limit check (Redis CL.THROTTLE or INCR fallback)
            → If allowed:
              → Load conversation history (Dapr state store → Redis)
              → Semantic sutta search (Redis Search, all-MiniLM-L6-v2 embeddings)
              → Build RAG prompt: system prompt + sutta context + history + user message
              → Call LEGO MPS (Anthropic Messages API via Bedrock proxy)
              → Save user message + response to conversation history
              → Publish response to "responses" topic
                → lbob-telegram receives response
                  → Send to Telegram Bot API
                    → User sees response
```

## Key Modules

### `openai_service_worldofgeese/`

| Module | Purpose |
|--------|---------|
| `__main__.py` | FastAPI app, Dapr subscription handler, LLM call via raw httpx |
| `rag.py` | RAG pipeline: assembles system prompt + sutta context + history |
| `sutta_search.py` | Vector embedding + Redis Search for semantic sutta retrieval |
| `seeker_state.py` | Conversation history via Dapr state store (trio-wrapped sync DaprClient) |
| `rate_limiter.py` | Per-user rate limiting (redis-cell with INCR fallback) |
| `init_secrets.py` | Secret initialization from Dapr secret store |

### `telegram_service/`

| Module | Purpose |
|--------|---------|
| `main.py` | Triogram bot: receives messages, publishes/subscribes via Dapr |

## Technology Choices

- **Python 3.12** with **trio** (not asyncio). DaprClient is sync-only; wrapped via `trio.to_thread.run_sync`.
- **sentence-transformers** (`all-MiniLM-L6-v2`): Local embeddings, 384 dimensions. CPU-only PyTorch to keep image small (~300MB vs 2GB+ with CUDA).
- **Redis Stack** (`redis/redis-stack-server`): Includes RediSearch (vector search), RedisJSON, redis-cell (rate limiting).
- **LEGO MPS**: Anthropic Claude via LEGO's Bedrock proxy. Requires `Accept: application/json` header and `Authorization: Bearer` (not `x-api-key`). LiteLLM can't be used — sends incompatible headers.
- **Rootless Podman** with `DOCKER_BUILDKIT=0`.

## Dapr Components

Located in `.dapr/components/`:

| Component | Type | Backing |
|-----------|------|---------|
| `redis-pubsub` | pubsub.redis | Redis 6379 |
| `statestore` | state.redis | Redis 6379 |

## Sutta Corpus

25 curated suttas in `sutta_corpus/suttas.json`. Sources: Access to Insight, SuttaCentral (CC0/public domain). Embedded via `scripts/embed_suttas.py` into Redis as JSON documents with 384-dim float32 vectors. Index name: `sutta_idx`.

## Environment Variables

| Variable | Service | Purpose |
|----------|---------|---------|
| `ANTHROPIC_AUTH_TOKEN` | openai | LEGO MPS Bearer token |
| `ANTHROPIC_BASE_URL` | openai | LEGO MPS endpoint |
| `LITELLM_MODEL` | openai | Model identifier |
| `REDIS_HOST` | openai | Redis hostname (default: lbob-redis) |
| `REDIS_PORT` | openai | Redis port (default: 6379) |
| `RATE_LIMIT_COUNT` | openai | Max requests per period (default: 20) |
| `RATE_LIMIT_PERIOD` | openai | Period in seconds (default: 3600) |
| `TRIOGRAM_TOKEN` | telegram | Telegram Bot API token |

## Phase Roadmap

See `docs/vision.html` for the full vision. Summary:

- **Phase 1 (Memory & Search)** — ✅ Complete: State store, sutta vectors, RAG pipeline, rate limiting
- **Phase 2 (Actors & Personality)** — Planned: Dapr Actors per seeker, adaptive tone, multi-tradition routing
- **Phase 3 (Guided Practice)** — Planned: Dapr Workflows for guided meditations, practice journaling
