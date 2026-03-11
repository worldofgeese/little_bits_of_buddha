# CONTINUE_PROMPT.md — Little Bits of Buddha

> Everything a future agent needs to continue working on LBOB.
> Last updated: 2026-03-11, after CI fix marathon.

## Current State

**All CI green** (run 186). Tests pass, lint clean, container builds.

## Repo

```
ssh://forgejo@paphos.hound-celsius.ts.net/kypris/little_bits_of_buddha.git
https://paphos.hound-celsius.ts.net/kypris/little_bits_of_buddha
```

## Source Layout

```
src/
  wisdom_service/       — Core: /wisdom/ask endpoint, RAG, Anthropic client, prompts, tools
  telegram_bot_service/ — Telegram bot (triogram/trio)
  openai_service/       — LiteLLM routing
  seeker_actor_service/ — Dapr actor for per-user state
  meditation_workflow_service/ — Dapr workflows for guided meditation
tests/
  test_wisdom_service.py    — Unit tests (async trio, respx mocks for httpx)
  test_meditation_workflows.py — Integration tests (require Dapr)
  test_integration.py       — Full integration tests
  test_langcache.py         — Langcache (cosine similarity) tests
  test_rate_limiter.py      — Rate limiter tests
scripts/
  run-tests.sh              — CI test runner (includes preflight check)
  run-lint.sh               — CI lint runner (ruff + ty)
  run-build.sh              — Container build
  check-ci-preflight.sh     — Dep availability check (fails fast if missing)
  ralph/                    — Ralph loop context (CLAUDE.md, progress.txt, prd.json)
```

## Key Technical Details

- **Async framework:** trio (NOT asyncio). Tests use `@pytest.mark.trio`
- **HTTP mocking:** respx library intercepts httpx at transport level (works for both sync and async)
- **Test client:** `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")`
- **Anthropic proxy:** `_call_anthropic_proxy()` in `anthropic_client.py` uses sync `httpx.Client()` — expects Anthropic API format response (`content[0].text`), NOT LiteLLM format
- **Tool calling:** `call_anthropic_with_tools()` in `tools.py` — also sync httpx, also Anthropic format
- **ty.toml:** `unresolved-import = "warn"`, `invalid-argument-type = "warn"` — because dapr-ext-workflow stubs don't resolve in CI
- **Pre-commit:** ruff check + ruff format + ty check (via prek)

## What's Next

Potential work areas (no specific phase plan yet):
1. Deploy to production (Docker Compose on paphos with Dapr sidecars)
2. Sutta index improvements (better vector embeddings, more suttas)
3. Meditation workflow completion (breathing, metta, body scan)
4. Seeker progression system (level detection, practice recommendations)
5. Integration test environment (local Dapr + Redis for CI)

## Constraints

- Do NOT use Claude Code / Anthropic proxy for development — GitHub Copilot models only
- Scripts-only CI workflows (no actions/*)
- Test with `pytest -m "not integration" -v` — integration tests need full Dapr environment
- Push to `main` branch directly (no PR workflow currently)
