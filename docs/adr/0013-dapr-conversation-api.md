# ADR 0013: Use Dapr Conversation API for LLM Calls

**Status:** Accepted (with fallback)

**Date:** 2026-03-05

**Context:**

Phase 2 extracts the LLM + RAG pipeline into a dedicated `wisdom-service`. Previously (ADR 0009), we used raw httpx to call the Anthropic proxy. Dapr 1.14+ introduces the alpha Conversation API, which provides infrastructure-level features for LLM calls:

- **Automatic caching**: Same question = cached response, saves LLM costs
- **PII scrubbing**: Removes sensitive data before sending to LLM
- **Circuit breakers**: Automatic retry and circuit breaking on failures
- **Observability**: Built-in metrics and tracing for LLM calls

The Conversation API is configured via a Dapr component (`.dapr/components/conversation.yaml`) and called via the Dapr SDK or HTTP.

**Decision:**

Use Dapr Conversation API as the **primary** LLM client in `wisdom-service`, with raw httpx as a **fallback**.

Implementation:
1. `conversation_client.py` calls Dapr Conversation API
2. If the API is unavailable (alpha instability, missing component, SDK gaps), fall back to `anthropic_client._call_anthropic_proxy()`
3. Log warnings when using fallback, so we can monitor Conversation API stability

This supersedes ADR 0009 (raw httpx only). Raw httpx remains as the fallback path.

**Consequences:**

**Positive:**
- Caching reduces LLM costs (duplicate questions across users get cached responses)
- PII scrubbing improves privacy compliance
- Circuit breakers improve resilience
- Infrastructure handles retries, we remove retry logic from application code

**Negative:**
- Conversation API is alpha: breaking changes possible, SDK may be incomplete
- Need runtime fallback detection (try Conversation API, catch exception, fall back)
- Fallback path increases complexity (two code paths to maintain)

**Mitigation:**
- Keep raw httpx fallback well-tested (existing tests from ADR 0009)
- Monitor logs for fallback usage frequency
- If Conversation API proves unstable, we can flip to fallback-only mode via feature flag

**Related ADRs:**
- ADR 0009: Raw httpx for Anthropic proxy (now the fallback)
- ADR 0012: Dapr Actors for seeker state (actors call wisdom-service)
