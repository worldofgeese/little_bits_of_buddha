# ADR 0001: Fix Secret Initialization Race Condition

## Status
Accepted

## Date
2026-02-10

## Context

Both services (`telegram_bot_service` and `openai_service`) have a race condition in their startup sequence. The issue manifests in two ways:

1. **Double `task_status.started()` calls**: The sync functions (`wait_for_dapr_ready`, `init_secrets`) call `task_status.started()`, and then the async wrappers call it again after `run_sync` returns. This causes Trio to raise an error or behave unexpectedly.

2. **Token read before secret loaded**: In `telegram_bot_service`, `triogram.make_bot()` reads `TRIOGRAM_TOKEN` from the environment at construction time. If `init_secrets()` hasn't completed, the token won't be available.

### Current (broken) flow:
```python
async def async_init_secrets(task_status=trio.TASK_STATUS_IGNORED):
    result = await to_thread.run_sync(init_secrets)
    task_status.started()  # Called here...
    return result

def init_secrets():
    # ... loads secret into os.environ
    # task_status is not even accessible here, but the pattern suggests
    # the original author intended to signal from within
```

The `wait_for_dapr_ready` function *does* receive `task_status` but calls `.started()` inside the sync context, which is problematic when wrapped in `run_sync`.

## Decision

Fix the initialization sequence by:

1. **Remove `task_status` from sync functions** — they don't need it; the async wrapper handles signaling.

2. **Call `.started()` only in async wrappers** — after the sync work completes.

3. **Ensure bot creation happens after secrets are loaded** — the `await nursery.start()` pattern already guarantees this, once the double-call is fixed.

## Consequences

### Positive
- Services start reliably without race conditions
- Clear separation: sync functions do work, async wrappers handle Trio coordination
- No functional changes to the services themselves

### Negative
- None identified

## Implementation

### telegram_bot_service_worldofgeese/__init__.py
Remove `task_status` parameter from `init_secrets()` (it was never used correctly).

### telegram_bot_service_worldofgeese/__main__.py
- Remove `task_status` from `wait_for_dapr_ready()` sync function
- Keep `task_status` only in async wrappers
- Call `.started()` once, after sync work completes

### openai_service_worldofgeese/__main__.py
Same changes as telegram service.
