# LBOB Vision — Phase 1 Plan: Memory & Search

## Goal
Transform LBOB from stateless chatbot to a bot that remembers conversations and retrieves relevant suttas via semantic search.

## Components (5 work packages, parallelizable in groups)

### WP1: Dapr State Store — Per-User Conversation History
**Branch:** `feat/state-store`
- Add Dapr state store component config (Redis-backed, already in stack)
- Create `seeker_state.py` module: save/load conversation history per `chat_id`
- Inject last N messages as context into LLM calls
- Tests: unit (mock Dapr client) + integration (real state store)

### WP2: Redis Vector Search — Sutta Embeddings
**Branch:** `feat/sutta-vectors`
- Create `sutta_corpus/` with curated excerpts from Access to Insight / SuttaCentral (public domain)
- Script to embed suttas via LEGO MPS embeddings endpoint (or local model)
- Redis Search index with vector field
- `sutta_search.py` module: semantic search given user query
- Tests: unit (mock Redis) + integration (real Redis with test vectors)

### WP3: RAG Pipeline — Context Injection
**Branch:** `feat/rag-pipeline`
**Depends on:** WP1 + WP2
- Wire sutta search results + conversation history into LLM prompt
- Update system prompt to cite retrieved suttas
- Structured prompt template: system + retrieved suttas + conversation history + user message
- Tests: prompt construction unit tests + integration test with real search

### WP4: Dapr Conversation API (stretch)
**Branch:** `feat/dapr-conversation`
- Replace raw httpx with Dapr Conversation building block
- Get response caching + PII scrubbing for free
- Requires Dapr 1.14+ — verify version in our stack
- May be blocked if LEGO MPS isn't a supported Dapr Conversation backend

### WP5: Redis-Cell Rate Limiting
**Branch:** `feat/rate-limiting`
- Add redis-cell module to Redis config
- Per-user rate limiting (e.g., 20 messages/hour)
- Graceful response when rate-limited ("Take a moment to reflect...")
- Tests: unit + integration

## Dispatch Strategy
- **WP1 + WP2**: Parallel (independent). Two ACP Agent Teams workers.
- **WP3**: Sequential after WP1 + WP2 merge.
- **WP4**: Research spike first — verify Dapr Conversation API compatibility with LEGO MPS. May defer.
- **WP5**: Independent, can run parallel with anything.

## Execution Order
```
Round 1 (parallel):  WP1 (state store) + WP2 (sutta vectors) + WP5 (rate limiting)
Round 2 (sequential): WP3 (RAG pipeline) — depends on WP1 + WP2
Research:             WP4 (Dapr Conversation API) — spike, may defer to Phase 2
```

## E2E Verification
After all WPs merge:
1. `podman compose up` the full stack
2. Send message to @LittleBitsOfBuddhaBot
3. Verify: response cites a relevant sutta
4. Send follow-up — verify: bot remembers previous message
5. Spam 25 messages quickly — verify: rate limiting kicks in
6. Stack healthy for 5 minutes

## Constraints
- Python 3.11, PDM + uv + ruff + ty
- Dapr architecture preserved (two microservices + sidecars)
- Rootless Podman, `DOCKER_BUILDKIT=0`
- All sutta texts must be from public domain sources
- Redis modules (RediSearch, redis-cell) need to be in the Redis container image
