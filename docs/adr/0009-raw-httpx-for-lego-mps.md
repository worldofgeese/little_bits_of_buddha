# ADR-0009: Raw httpx for LEGO MPS Instead of LiteLLM

**Date:** 2026-03-03
**Status:** Accepted
**Deciders:** Tao Hansen, Kypris

## Context

LEGO MPS (`ANTHROPIC_PROXY_HOST/claude`) is a Bedrock proxy that exposes the Anthropic Messages API. The original implementation used LiteLLM with `anthropic/` provider prefix.

## Problem

LiteLLM always sends an `x-api-key` header for `anthropic/` prefixed models. LEGO MPS returns `406 Not Acceptable` when both `Authorization` and `x-api-key` headers are present. Additionally, LEGO MPS requires an explicit `Accept: application/json` header that the Anthropic SDK sends but raw httpx doesn't by default.

## Decision

Replace LiteLLM with raw httpx calls in `_call_lego_mps()`.

## Consequences

- We control headers exactly: `Authorization: Bearer`, `Accept: application/json`, `anthropic-version: 2023-06-01`.
- We manually convert between Anthropic Messages API format and the internal message format.
- We lose LiteLLM's model-agnostic interface, retries, and cost tracking.
- If we ever switch LLM providers, we'll need to update the httpx code or reintroduce an abstraction.
- The `LITELLM_MODEL` env var is kept for configuration but the `anthropic/` prefix is stripped before sending to LEGO MPS.
