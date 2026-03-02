# Task: Get Little Bits of Buddha Working End-to-End with LEGO MPS

## Context
This is a Telegram bot (`@LittleBitsOfBuddhaBot`) that speaks as the Buddha. It uses:
- Python 3.11, FastAPI, triogram (Telegram), Dapr pub/sub with Redis
- Two microservices: `telegram_bot_service_worldofgeese` (receives messages) and `openai_service_worldofgeese` (calls LLM)
- LiteLLM for LLM calls

**Repo:** `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`
**Branch:** Create and work on `feat/lego-mps-integration`

## What Needs to Change

### 1. Switch LiteLLM from OpenAI to LEGO MPS (Anthropic-compatible)

The LEGO MPS endpoint is an Anthropic Messages API proxy:
- **Base URL:** `https://models.assistant.legogroup.io/claude`
- **Auth:** Bearer token via `ANTHROPIC_AUTH_TOKEN` env var (already set in devbox)
- **Model:** `anthropic.claude-sonnet-4-5-20250929-v1:0`

LiteLLM supports custom Anthropic endpoints. The `completion()` call needs:
```python
response = completion(
    model="anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0",
    api_base="https://models.assistant.legogroup.io/claude",
    api_key=os.environ.get("ANTHROPIC_AUTH_TOKEN"),
    messages=[...],
)
```

**Important:** LiteLLM auto-appends `/v1/messages` to `api_base` for Anthropic provider. Verify that `https://models.assistant.legogroup.io/claude/v1/messages` is the correct full endpoint. If LEGO MPS expects a different path, you may need to adjust.

### 2. Update `src/openai_service_worldofgeese/__main__.py`
- Replace the `completion()` call to use Anthropic provider with LEGO MPS
- Change `LITELLM_MODEL` env default from `gpt-4o-mini` to `anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0`
- Change `api_key` source from `OPENAI_API_KEY` to `ANTHROPIC_AUTH_TOKEN`
- Add `api_base` parameter pointing to LEGO MPS

### 3. Update `src/openai_service_worldofgeese/__init__.py`
- The `init_secrets()` function fetches from Dapr secret store and sets `OPENAI_API_KEY`
- Update to set `ANTHROPIC_AUTH_TOKEN` instead (or make it configurable)
- Update the secret key name from `openai-secret` to `anthropic-secret` (or keep as-is and just change the env var it sets)

### 4. Update `secrets/secrets.json`
Currently:
```json
{
  "telegram-secret": "6014356103:AAFMthhrKMXJLdeuU3rK09ViK27bCJiJTlw",
  "openai-secret": "sk-proj-..."
}
```

Change to:
```json
{
  "telegram-secret": "6014356103:AAFMthhrKMXJLdeuU3rK09ViK27bCJiJTlw",
  "anthropic-secret": "6a7f7bb5919644abbcc1e90caa69627d:5ltYvTeokfT9W734Uvr0qmDT1RrDTdiiyu1dFbiFlkC_A2Ftg6nvydg54DsLewTtvt6jot-NA1Tp46i7qZWh2ADYR-rG6yzxfDOdPsWR2pO9rycquqYwtjQ7MU7CRnumB3Dp5Nu3jsuITTXV3niOrRMFuWVmkidNSI1ay-cHnkI3GCP-MG8Bb-ex1yLMtsBr9cDWSrzD0IGM_hHsGIGaMcdrJZC2Ht5FrvCuiTsZO4-BDfDE-W19709TK9PaGi3446jmVcUjDW8bEGaUy9Rh52tLXoYZGiwlRYEGvocfqOzaqdvCGuc_rfzjfPz1ExpvCQ3tov4k-XS4Nq3PDCaNlg"
}
```

### 5. Update environment references
- `compose.yaml`: Change `OPENAI_API_KEY` to `ANTHROPIC_AUTH_TOKEN` for the openai-service container
- `dapr.yaml`: No changes needed (Dapr config is fine)
- Add `ANTHROPIC_BASE_URL=https://models.assistant.legogroup.io/claude` as env var in compose.yaml for the openai-service

### 6. Update tests
Check `tests/` for any tests that mock the OpenAI completion call and update them to use the new Anthropic provider format.

### 7. Verify LiteLLM call works
Write a small integration test or script that calls:
```python
from litellm import completion
response = completion(
    model="anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0",
    api_base="https://models.assistant.legogroup.io/claude",
    api_key="<token>",
    messages=[{"role": "user", "content": "Hello"}],
)
print(response)
```
Run this to verify the LiteLLM → LEGO MPS path works before touching the rest.

## Constraints
- Keep the Dapr microservices architecture (do NOT simplify to single service)
- Keep triogram for Telegram (do NOT replace with python-telegram-bot or similar)
- Use PDM for dependency management
- Use ruff for linting, ty for type checking
- Do NOT remove or rename the services — just update the LLM provider

## TDD
Write failing tests FIRST for the new Anthropic provider configuration. Commit them.
Then implement until tests pass. Commit again.

## Self-Review (mandatory before final commit)
Re-read your entire diff (`git diff main..HEAD`). Write out:

**Concerns (list exactly 3):**
1. [Something specific that could break]
2. [An edge case you didn't test]
3. [An assumption you're uncertain about]

**TDD compliance check:**
- [ ] I committed failing tests BEFORE implementation
- [ ] Tests and implementation are in separate commits
- [ ] All tests pass

Commit and push to `feat/lego-mps-integration`.
Do NOT merge to main — the orchestrator handles merge after review.
