# Task: WP5 — Phase 2 Infrastructure (Compose, Dockerfiles, Dapr Components)

## Context

Little Bits of Buddha (LBOB) is a Telegram chatbot being upgraded from Phase 1 (stateless) to Phase 2 (Dapr Actors per user). This task sets up the infrastructure: compose.yaml, Dockerfiles, and Dapr component configs for the new two-service topology.

**Repo:** `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`
**Python:** 3.12+
**Branch:** `feat/phase2-infra`
**Rootless Podman:** `DOCKER_HOST=tcp://podman-in-podman:2375`, `DOCKER_BUILDKIT=0`

Read `phase2-plan.md` in the repo root for full architectural context.

## What to Build

### 1. Update `compose.yaml`

**Remove (production profile):**
- `openai-service` container
- `openai-dapr` sidecar

**Add (production profile):**

```yaml
  # --- Seeker Actor Service (hosts Dapr Actors) ---
  seeker-actor-dapr:
    image: lbob-daprd:latest
    build:
      context: .
      dockerfile: Dockerfile.daprd
    container_name: lbob-seeker-actor-dapr
    networks:
      - lbob
    command:
      - ./daprd
      - --app-id=seeker-actor-service
      - --app-channel-address=lbob-seeker-actor
      - --app-port=8081
      - --dapr-http-port=3500
      - --dapr-grpc-port=50001
      - --resources-path=/components
      - --log-level=info
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    profiles:
      - production

  seeker-actor-service:
    image: lbob-seeker-actor:latest
    build:
      context: .
      dockerfile: Dockerfile
      target: seeker-actor-service-production
    container_name: lbob-seeker-actor
    networks:
      - lbob
    depends_on:
      redis:
        condition: service_healthy
    environment:
      - DAPR_HTTP_ENDPOINT=http://lbob-seeker-actor-dapr:3500
      - DAPR_GRPC_ENDPOINT=lbob-seeker-actor-dapr:50001
    ports:
      - "8081:8081"
    restart: unless-stopped
    profiles:
      - production

  # --- Wisdom Service (LLM + RAG, stateless) ---
  wisdom-dapr:
    image: lbob-daprd:latest
    build:
      context: .
      dockerfile: Dockerfile.daprd
    container_name: lbob-wisdom-dapr
    networks:
      - lbob
    command:
      - ./daprd
      - --app-id=wisdom-service
      - --app-channel-address=lbob-wisdom
      - --app-port=8080
      - --dapr-http-port=3500
      - --dapr-grpc-port=50001
      - --resources-path=/components
      - --log-level=info
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    profiles:
      - production

  wisdom-service:
    image: lbob-wisdom:latest
    build:
      context: .
      dockerfile: Dockerfile
      target: wisdom-service-production
    container_name: lbob-wisdom
    networks:
      - lbob
    depends_on:
      redis:
        condition: service_healthy
    environment:
      - ANTHROPIC_AUTH_TOKEN=${ANTHROPIC_AUTH_TOKEN}
      - ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL}
      - LITELLM_MODEL=anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0
      - REDIS_HOST=lbob-redis
      - DAPR_HTTP_ENDPOINT=http://lbob-wisdom-dapr:3500
      - DAPR_GRPC_ENDPOINT=lbob-wisdom-dapr:50001
    ports:
      - "8080:8080"
    restart: unless-stopped
    profiles:
      - production
```

**Keep unchanged:** redis, telegram-bot-service, telegram-bot-dapr, loki, promtail, networks, volumes.

**Update** `telegram-bot-dapr` if needed — its pub/sub subscription routing should still work (messages topic → the actor service subscribes to it).

### 2. Update `Dockerfile`

Add two new build targets after the existing ones:

**seeker-actor-service-production:**
```dockerfile
# --- seeker-actor-service ---
FROM base-builder as seeker-actor-service-builder
COPY src/seeker_actor_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.12-slim as seeker-actor-service-production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY --from=seeker-actor-service-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=seeker-actor-service-builder /usr/local/bin /usr/local/bin
WORKDIR /app
RUN useradd --create-home nonroot
USER nonroot
COPY --chown=nonroot:nonroot src/seeker_actor_service seeker_actor_service/
EXPOSE 8081
ENTRYPOINT ["python", "-m", "seeker_actor_service"]
```

**wisdom-service-production:**
```dockerfile
# --- wisdom-service ---
FROM base-builder as wisdom-service-builder
COPY src/wisdom_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.12-slim as wisdom-service-production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY --from=wisdom-service-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=wisdom-service-builder /usr/local/bin /usr/local/bin
WORKDIR /app
RUN useradd --create-home nonroot
USER nonroot
COPY --chown=nonroot:nonroot src/wisdom_service wisdom_service/
COPY --chown=nonroot:nonroot sutta_corpus/ sutta_corpus/
COPY --chown=nonroot:nonroot scripts/embed_suttas.py embed_suttas.py
COPY --chown=nonroot:nonroot scripts/entrypoint.sh entrypoint.sh
EXPOSE 8080
ENTRYPOINT ["bash", "/app/entrypoint.sh"]
```

### 3. Create stub service directories

These are stubs so the Dockerfile builds pass. The actual implementation comes in WP1 and WP2.

**`src/seeker_actor_service/__init__.py`** — empty
**`src/seeker_actor_service/__main__.py`:**
```python
"""Seeker Actor Service — stub for Phase 2 infrastructure.

Will host Dapr Virtual Actors (one per Telegram user).
"""
import trio
from fastapi import FastAPI
from hypercorn.config import Config
from hypercorn.trio import serve

app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

async def main():
    config = Config()
    config.bind = ["0.0.0.0:8081"]
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve, app, config)

if __name__ == "__main__":
    trio.run(main)
```

**`src/seeker_actor_service/requirements.txt`:**
```
dapr>=1.14.0
dapr-ext-fastapi>=1.14.0
fastapi>=0.115.0
hypercorn>=0.17.0
trio>=0.27.0
httpx>=0.28.0
```

**`src/wisdom_service/__init__.py`** — empty
**`src/wisdom_service/__main__.py`:**
```python
"""Wisdom Service — stub for Phase 2 infrastructure.

Will host LLM + RAG pipeline, called by SeekerActor via Dapr service invocation.
"""
import trio
from fastapi import FastAPI
from hypercorn.config import Config
from hypercorn.trio import serve

app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/wisdom/ask")
async def ask():
    return {"response": "stub", "suttas_cited": [], "detected_themes": []}

async def main():
    config = Config()
    config.bind = ["0.0.0.0:8080"]
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve, app, config)

if __name__ == "__main__":
    trio.run(main)
```

**`src/wisdom_service/requirements.txt`:**
```
dapr>=1.14.0
dapr-ext-fastapi>=1.14.0
fastapi>=0.115.0
hypercorn>=0.17.0
httpx>=0.28.0
redis>=5.0.0
numpy>=2.0.0
sentence-transformers>=3.0.0
trio>=0.27.0
```

### 4. New Dapr components

**`.dapr/components/conversation.yaml`:**
```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: anthropic-conversation
spec:
  type: conversation.anthropic
  version: v1
  metadata:
    - name: apiKey
      value: "${ANTHROPIC_AUTH_TOKEN}"
    - name: baseURL
      value: "${ANTHROPIC_BASE_URL}"
    - name: model
      value: "anthropic.claude-sonnet-4-5-20250929-v1:0"
    - name: cacheTTL
      value: "1h"
```

Note: The exact schema for the Dapr Conversation API component may differ from the above. **Check the Dapr docs** at `https://docs.dapr.io/reference/components-reference/supported-conversation/` for the correct schema. If the Anthropic component doesn't exist yet (it's alpha), create a placeholder YAML with a comment documenting what it will look like, and note in an ADR that raw httpx remains the runtime fallback.

**`.dapr/components/actor-statestore.yaml`:**
```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: statestore
spec:
  type: state.redis
  version: v1
  metadata:
    - name: redisHost
      value: lbob-redis:6379
    - name: redisPassword
      value: ""
    - name: actorStateStore
      value: "true"
```

This replaces the existing `statestore.yaml` — add `actorStateStore: "true"` to enable actor state persistence.

### 5. State migration script

**`scripts/migrate_state_to_actors.py`:**

Reads existing `seeker:{chat_id}` keys from Redis, transforms them into the new actor state format, and writes them as actor-compatible keys. 

```python
"""Migrate Phase 1 seeker state to Phase 2 actor state format.

Phase 1 format: key="seeker:{chat_id}", value=JSON array of messages
Phase 2 format: key depends on Dapr actor key scheme (typically "actors||{actorType}||{actorId}||{key}")

Run once during Phase 2 deployment.
"""
```

The actual key format depends on how Dapr stores actor state — research this and implement accordingly. The migration should:
1. Read all `seeker:*` keys
2. For each, create the actor state with: chat_id, practice_level="newcomer", conversation_count=len(history)//2, topics_explored=[], history=existing messages
3. Write to the new key format
4. Print a summary of migrated records
5. Do NOT delete old keys (manual cleanup after verification)

### 6. ADR

**`docs/adr/0012-dapr-actors-for-seeker-state.md`:**
Document why we're moving from flat state store to Dapr actors:
- Lifecycle management (activation/deactivation)
- Single-threaded guarantees per user (no concurrent state mutations)
- State persistence handled by runtime
- Foundation for future features (practice level, adaptive tone)

### 7. Tests

**`tests/test_phase2_infra.py`:**
1. Test that compose.yaml is valid YAML and contains expected services
2. Test that new Dapr component files exist and are valid YAML
3. Test that stub services have requirements.txt
4. Test that Dockerfile contains new build targets (grep for target names)
5. Test migration script can handle empty state and sample state data

## Constraints

- Use git worktrees if this runs parallel to WP3: `git worktree add ../lbob-wp5 -b feat/phase2-infra`
- Modify: `compose.yaml`, `Dockerfile`, `.dapr/components/`
- Create: `src/seeker_actor_service/`, `src/wisdom_service/`, `scripts/migrate_state_to_actors.py`, `docs/adr/0012-*`, `tests/test_phase2_infra.py`
- Do NOT modify existing service source code (telegram_bot_service, openai_service)

## Branch & Push

Work on branch: `feat/phase2-infra`. Commit AND push when done.
TDD: commit failing tests first, then implementation.

## Self-Review

Re-read diff. 3 concerns, TDD compliance check.
