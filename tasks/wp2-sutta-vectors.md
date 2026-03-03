# Task: WP2 — Redis Vector Search for Sutta Corpus

## Context
Project: Little Bits of Buddha (LBOB)
Stack: Python 3.11, FastAPI, Dapr, Redis, PDM, trio
Repo: `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`
Vision: `docs/vision.html` · Plan: `docs/phase1-plan.md`

## Branch
Create and work on branch: `feat/sutta-vectors`
Do NOT work on main.

## TDD
Write failing tests FIRST in `tests/test_sutta_search.py`. Commit them.
Then implement until tests pass. Commit again.

## What to do

1. **Curate sutta corpus** — create `sutta_corpus/` directory with a `suttas.json` file:
   - 20-30 key suttas from the Pali Canon (public domain, from Access to Insight / SuttaCentral)
   - Each entry: `{"id": "SN56.11", "title": "Dhammacakkappavattana Sutta", "collection": "SN", "text": "...", "themes": ["four noble truths", "middle way"]}`
   - Focus on: Four Noble Truths, Eightfold Path, Five Aggregates, Dependent Origination, mindfulness, compassion, suffering, impermanence, non-self
   - Keep excerpts under 2000 chars each (for embedding quality)

2. **Create `src/openai_service_worldofgeese/sutta_search.py`**:
   - `embed_text(text: str) -> list[float]` — call Anthropic proxy embeddings endpoint (or use a local sentence-transformers model via `sentence-transformers` package for simplicity)
   - `index_suttas(suttas: list[dict])` — create Redis Search index with vector field, embed and store all suttas
   - `search_suttas(query: str, top_k: int = 3) -> list[dict]` — semantic search, return top K results with scores
   - Use `redis.commands.search` (redis-py with RediSearch)

3. **Create `scripts/embed_suttas.py`** — CLI script to run indexing:
   - Load `sutta_corpus/suttas.json`
   - Call `index_suttas()`
   - Report: N suttas indexed, index size

4. **Redis container needs RediSearch module** — update `compose.yaml`:
   - Change Redis image from `redis:7` to `redis/redis-stack-server:latest` (includes RediSearch + RedisJSON)
   - Or add the module load if using custom Redis config

5. **Tests** (`tests/test_sutta_search.py`):
   - Test embed_text returns a vector of expected dimensionality
   - Test index_suttas creates index and stores documents (mock Redis)
   - Test search_suttas returns relevant results (mock Redis)
   - Test search with empty corpus returns empty list
   - Test sutta corpus JSON is valid and has required fields

## Embedding Strategy Decision
**Option A (recommended):** Use `sentence-transformers` with `all-MiniLM-L6-v2` (384-dim, fast, runs locally, no API cost)
**Option B:** Use Anthropic proxy embeddings endpoint (if available — check `${ANTHROPIC_BASE_URL}/v1/embeddings`)

Go with Option A unless Anthropic proxy embeddings are confirmed working. Add `sentence-transformers` to PDM dependencies.

## Constraints
- Only modify/create: `sutta_corpus/`, `src/openai_service_worldofgeese/sutta_search.py`, `scripts/embed_suttas.py`, `tests/test_sutta_search.py`, `compose.yaml` (Redis image only), `pyproject.toml` (add deps)
- Do NOT modify: telegram service, openai service __main__.py, Dapr components
- Sutta texts MUST be from public domain sources (Access to Insight is CC0, SuttaCentral is CC0)
- Keep embeddings model small — this runs in a container

## Branch & Push
Work on branch: `feat/sutta-vectors`. Commit AND push to the branch when done.

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
