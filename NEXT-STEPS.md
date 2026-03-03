# LBOB — Current State & Next Steps

> Last updated: 2026-03-03 by Kypris

## Current State: Phase 1 Complete ✅

The bot is **live and responding** via Telegram with sutta-augmented RAG responses.

### What's Working
- ✅ Telegram → Dapr pub/sub → LEGO MPS Claude → Dapr pub/sub → Telegram (full E2E)
- ✅ Per-user conversation memory (Dapr state store → Redis)
- ✅ Semantic sutta search (25 suttas embedded, all-MiniLM-L6-v2, Redis Search)
- ✅ RAG pipeline: sutta context + conversation history injected into LLM prompt
- ✅ Per-user rate limiting (redis-cell CL.THROTTLE with INCR fallback)
- ✅ 14 tests passing (7 RAG pipeline + 7 seeker state)
- ✅ CPU-only PyTorch in Dockerfile (~300MB, not 2GB)

### What Needs Fixing / Polish
- [ ] **Rebuild Docker image from main**: The running container was hot-patched (docker cp). Need a clean rebuild from `main` to bake in all fixes (sutta_search import path, tolist(), REDIS_HOST).
- [ ] **Sutta re-indexing on container start**: Currently `embed_suttas.py` must be run manually after deploy. Should be automated — either an init container or a startup hook.
- [ ] **E2E test with separate bot**: Tao wants tests to use a dedicated test bot/chat, not his personal Telegram (488228716). Need a test bot token + test chat ID.
- [ ] **WP4 research spike**: Dapr Conversation API compatibility with LEGO MPS. May not work if LEGO MPS isn't a supported backend. Could defer to Phase 2.
- [ ] **Expand sutta corpus**: Currently 25 suttas. Access to Insight has thousands. Need a scraping/curation pipeline.
- [ ] **Model caching**: First query after restart takes ~3s (model load). Could pre-warm on startup.

## Phase 2: Actors & Personality (Next)

From the vision doc:

1. **Dapr Actors**: One actor per seeker. Holds state, practice level, preferred tradition.
2. **Actor timers**: Daily mindfulness prompts, practice reminders.
3. **Adaptive tone**: Detect beginner vs practitioner from conversation patterns.
4. **Multi-tradition routing**: Theravada, Zen, secular — user picks or system infers.

### Phase 2 Prerequisites
- Dapr Actors require the placement service (already in stack as `lbob-placement`).
- Python Dapr SDK supports actors but docs are sparse. Spike needed.
- Actor state vs current seeker_state: Actors manage their own state lifecycle. Could replace `seeker_state.py` or wrap it.

## Phase 3: Guided Practice (Future)

1. **Dapr Workflows**: Multi-step guided meditations that survive restarts.
2. **Structured learning paths**: Four Noble Truths → Eightfold Path → practices.
3. **Practice journaling**: User logs sits, bot tracks patterns.
4. **Redis TimeSeries**: Community-level practice analytics.

## Key Infrastructure Notes

- **Container restart order**: Stop both → start app → start sidecar. Dapr sidecar uses `network_mode: "service:<app>"`.
- **LEGO MPS headers**: Must send `Accept: application/json` + `Authorization: Bearer`. No `x-api-key`.
- **Redis hostname**: Set `REDIS_HOST=lbob-redis` in container env. Default `localhost` only works for local dev.
- **sutta_search.py import**: Uses `redis.commands.search.index_definition` (lowercase), NOT `indexDefinition`.
- **Embeddings stored as list[float]**: RedisJSON needs `.tolist()`, not `.tobytes()`.

## Git State

- **Latest commit on main**: `68f95ff` (REDIS_HOST compose env fix)
- **Remote**: `ssh://forgejo@paphos.hound-celsius.ts.net/kypris/little_bits_of_buddha.git`
- **All Phase 1 WPs merged**: WP1 (state store), WP2 (sutta vectors), WP3 (RAG pipeline), WP5 (rate limiting)
- **Tests**: 14 passing, 1 xfail (handler integration)

## Running Containers

```
lbob-telegram        + lbob-telegram-dapr   (telegram service)
lbob-openai          + lbob-openai-dapr     (openai/wisdom service)
lbob-redis                                   (Redis Stack)
lbob-placement                               (Dapr placement, for future actors)
```

Bot: `@LittleBitsOfBuddhaBot` | Token env: `TRIOGRAM_TOKEN`
