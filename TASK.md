# Task: Fix 406 Not Acceptable from Anthropic proxy

## Context
`src/openai_service_worldofgeese/__main__.py` in `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`.
The `_call_anthropic_proxy` function sends requests to Anthropic proxy (an Anthropic-compatible proxy).
It's returning `406 Not Acceptable`.

## Root Cause
The `anthropic-version` header is missing from the request headers. The working curl command includes:
```
-H "anthropic-version: 2023-06-01"
```

But the code only sends `Content-Type` and `Authorization`.

## What to do
1. In `_call_anthropic_proxy()`, add `"anthropic-version": "2023-06-01"` to the `headers` dict.
2. Run `cd /home/node/.openclaw/workspace/projects/little_bits_of_buddha && python -m pytest tests/ -v` to verify tests still pass.
3. Commit to a branch `fix/406-anthropic-version` and push.

## Constraints
- Only modify: `src/openai_service_worldofgeese/__main__.py`
- Do NOT modify any other files unless tests need updating
- Do NOT change the overall httpx approach — just add the missing header
