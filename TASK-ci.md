# Task: Fix CI Test Failures

## Context
Project: `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`
CI runs `pytest -m "not integration" -v` and is failing with 10 test failures.

## Failing Tests & Root Causes

### 1. tests/test_integration.py — STALE (references old architecture)
- `TestMessageFlow::test_telegram_service_can_be_imported` — `libstdc++.so.6` missing (triogram native dep)
- `TestMessageFlow::test_message_subscriber_registration` — same import error
- `TestMessageFlow::test_check_message_function_exists` — `check_message` function doesn't exist anymore
- `TestDaprConfiguration::test_secret_store_component_exists` — checks for `.dapr/components/local-secret-store.yaml` which was deliberately deleted
- `TestLiteLLMIntegration::test_litellm_completion_callable` — LiteLLM was replaced with raw httpx
- `TestLiteLLMIntegration::test_litellm_response_format` — same
- `TestEndToEndFlow::test_complete_message_flow` — same import issues

### 2. tests/test_openai_service.py — IMPORT FAILURES  
- `TestBuildApp::test_build_app_returns_tuple` — `dapr.ext.fastapi` not importable (package split?)
- `TestBuildApp::test_build_app_has_subscriber_decorator` — same
- `TestAnthropicProviderConfig::test_completion_uses_anthropic_proxy_helper` — `dapr.clients` not importable

### 3. tests/test_anthropic_proxy_integration.py — CORRECTLY MARKED
- Already has `@pytest.mark.integration` — should be skipped by CI. Verify.

## What To Do

1. **Read the current source files first:**
   - `src/openai_service_worldofgeese/__main__.py` — understand current API
   - `src/openai_service_worldofgeese/__init__.py` — understand imports
   - `src/telegram_bot_service_worldofgeese/__init__.py` — understand imports

2. **Fix `tests/test_integration.py`:**
   - Remove or update `TestDaprConfiguration::test_secret_store_component_exists` (file was deleted)
   - Remove `TestLiteLLMIntegration` class entirely (LiteLLM replaced with raw httpx)
   - Mark telegram import tests as `@pytest.mark.integration` (need triogram native lib)
   - Update `TestEndToEndFlow` to use the new httpx-based `_call_anthropic_proxy` function

3. **Fix `tests/test_openai_service.py`:**
   - Mock `dapr.ext.fastapi` and `dapr.clients` imports properly so tests run without dapr installed
   - OR mark tests that need real dapr as integration tests

4. **Verify with:** `pytest -m "not integration" -v`
   All remaining tests must pass.

5. **Commit** to branch `fix/ci-tests` and push to origin.

## Constraints
- `DOCKER_BUILDKIT=0` for any docker commands
- Use `--no-verify` for git commits (pre-commit hooks have known issues)
- Do NOT modify application source code — only test files and CI config
- Keep all currently passing tests passing
- The 14 currently passing tests MUST still pass
