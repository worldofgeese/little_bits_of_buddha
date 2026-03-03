# Task: Update All LBOB Dependencies + openclaw-config Compose to Latest Versions

## Context
Two repos need dependency updates:
1. `/tmp/openclaw-config/compose.yaml` — production compose with pinned image versions
2. `/home/node/.openclaw/workspace/projects/little_bits_of_buddha` — Python project with Dockerfile, compose.yaml, requirements.txt

Use `context7` to look up latest versions of each dependency. Add `use context7` to your queries when checking docs.

## What to Do

### Phase 1: Research latest versions
For each dependency, look up the current latest stable version:

**Container images (in openclaw-config compose.yaml):**
- `redis:7-alpine` → check if Redis 8.x is stable (Redis 8.4 is out)
- `daprio/daprd:1.14.4` → check latest Dapr release
- `postgres:17` → check latest PostgreSQL
- `qdrant/qdrant:latest` → verify latest tag
- `forgejo/runner:11` → check latest Forgejo runner

**Python deps (in little_bits_of_buddha):**
- Python base image: `python:3.11-slim` → check if 3.12 or 3.13 works with trio (NOT 3.14 — trio incompatible)
- `trio>=0.25.0` → latest trio
- `httpx>=0.24.0` → latest httpx  
- `fastapi` → latest fastapi
- `hypercorn` → latest hypercorn
- `attrs` → latest attrs
- `triogram` — pinned to git commit, leave as-is

**Dapr sidecar:**
- `daprio/daprd:1.14.4` in Dockerfile.daprd → latest stable

### Phase 2: Update files
1. Update `requirements.txt` files in both services with new minimum versions
2. Update `Dockerfile` base image if Python version can be bumped
3. Update `Dockerfile.daprd` with latest daprd version
4. Update `/tmp/openclaw-config/compose.yaml` image tags

### Phase 3: Test
1. Build the Docker images: `DOCKER_BUILDKIT=0 docker build --target telegram-bot-service-production -t lbob-telegram:test -f Dockerfile .`
2. Build: `DOCKER_BUILDKIT=0 docker build --target openai-service-production -t lbob-openai:test -f Dockerfile .`
3. Build: `DOCKER_BUILDKIT=0 docker build -t lbob-daprd:test -f Dockerfile.daprd .`
4. Run tests if possible (venv may be broken — try `python -m pytest tests/ -v` or skip if env issues)

### Phase 4: Commit
1. In `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`: commit to branch `chore/update-deps` and push
2. In `/tmp/openclaw-config`: commit to branch `chore/update-deps` and push to `origin`

## Constraints
- Do NOT use Python 3.14 — trio is incompatible
- Do NOT change triogram (pinned to specific git commit for compatibility)
- `DOCKER_BUILDKIT=0` is required for all docker builds (cgroup issue)
- Do NOT modify application logic — only dependency versions and image tags
- If a build fails after version bump, try the next lower version or revert that specific dep
- The openclaw-config repo is at `/tmp/openclaw-config` (already cloned)

## Known Issues
- triogram pins `trio==0.22.*` but we install with `--no-deps` and manage trio separately
- `ty check` has pre-existing errors — use `--no-verify` for git commits if pre-commit blocks

## Self-Review
After all changes, verify:
1. All Docker images build successfully
2. No import errors when containers start
3. Version bumps are conservative (stable releases only, no RCs/betas)
