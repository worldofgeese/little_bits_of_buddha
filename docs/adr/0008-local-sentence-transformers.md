# ADR-0008: Local Sentence Transformers for Sutta Embeddings

**Date:** 2026-03-03
**Status:** Accepted
**Deciders:** Tao Hansen, Kypris

## Context

Phase 1 requires vector embeddings for semantic sutta search. Two options:

1. **LEGO MPS embeddings endpoint** — use the same Bedrock proxy that serves LLM calls
2. **Local sentence-transformers** — run `all-MiniLM-L6-v2` in the container

## Decision

Use `sentence-transformers` with `all-MiniLM-L6-v2` locally.

## Rationale

- **No API cost**: Embeddings are computed at indexing time and query time without network calls to LEGO MPS.
- **No auth complexity**: LEGO MPS requires specific header handling (Accept: application/json, Bearer token). Adding embedding support would mean more fragile httpx code.
- **Speed**: Local embedding of 25 suttas takes ~2 seconds. Query embedding takes ~50ms. Network round-trip to LEGO MPS would add 200-500ms per query.
- **Model size**: `all-MiniLM-L6-v2` is 80MB. CPU-only PyTorch adds ~300MB to the container. Acceptable for a server-side container.
- **Quality**: 384-dim embeddings from MiniLM are sufficient for a 25-sutta corpus. Not competing with state-of-the-art retrieval benchmarks.

## Consequences

- Container image is ~500MB larger than without ML deps.
- Must use `--index-url https://download.pytorch.org/whl/cpu` in Dockerfile to avoid 2GB CUDA wheels.
- First query after container start has ~3s cold start (model loading). Subsequent queries are instant.
- If corpus grows to thousands of suttas, may need to revisit embedding strategy.
