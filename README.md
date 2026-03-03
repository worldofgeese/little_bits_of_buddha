# Little Bits of Buddha

<figure>
  <img src="https://us-east-1.linodeobjects.com/kinopio-uploads/wvF4LRNvUWaQyrINvklmE/little-bits-of-buddha-telegram-bot-logo--SNM.jpg" alt="A robotic monk with a wheel-maze for a head against a blue field" width="250" />
</figure>

A Telegram bot that speaks as the Buddha, responding to users with teachings in the style of the Early Buddhist Canon.

**Try it:** [@LittleBitsOfBuddhaBot](https://t.me/LittleBitsOfBuddhaBot)

## Architecture

Two microservices communicate via [Dapr](https://dapr.io/) pub/sub over Redis.

```
User ──► Telegram API
              │
              ▼
   ┌─────────────────────┐         pub/sub          ┌──────────────────────┐
   │ telegram-bot-service │ ──── "messages" ──────► │    openai-service     │
   │   (triogram/trio)    │ ◄─── "responses" ────── │  (httpx → Anthropic proxy)  │
   └─────────────────────┘       (Redis)            └──────────────────────┘
         ▲  │                                               │
         │  └── Dapr sidecar (daprd)                        └── Dapr sidecar (daprd)
         │
         ▼
   Telegram API
```

**Pipeline flow:**
1. User sends message → Telegram Bot API → triogram polls `getUpdates`
2. `telegram-bot-service` publishes `{chat_id, text}` to Dapr topic `messages`
3. `openai-service` receives message, calls Anthropic proxy (Anthropic Claude via Bedrock proxy)
4. `openai-service` publishes `{chat_id, text}` to Dapr topic `responses`
5. `telegram-bot-service` receives response, sends via Telegram `sendMessage`

**Services:**
- `telegram-bot-service` — Trio-based Telegram bot (triogram), FastAPI for Dapr subscription callbacks
- `openai-service` — FastAPI + Trio, calls LLM via raw httpx (not LiteLLM — see ADR below)

**Infrastructure:**
- [Dapr](https://dapr.io/) 1.14.4 — Pub/sub messaging via Redis Streams
- [Redis](https://redis.io/) 7 — Message broker
- [Podman](https://podman.io/) — Rootless container runtime

## Operator Guide (Production)

### Prerequisites

- Podman (or Docker) with compose support
- Images built locally (see Building below)

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) | `6014356103:AAF...` |
| `ANTHROPIC_AUTH_TOKEN` | Anthropic proxy Bearer token (full `uuid:secret` format) | `6a7f7bb5...:5ltY...` |

Optional (defaults in compose):
| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_BASE_URL` | `${ANTHROPIC_BASE_URL}` | LLM API base URL |
| `LITELLM_MODEL` | `anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0` | Model identifier |

### Building

```bash
cd little_bits_of_buddha

# Build all images (DOCKER_BUILDKIT=0 required for rootless Podman cgroup workaround)
DOCKER_BUILDKIT=0 podman build --target telegram-bot-service-production -t lbob-telegram:latest .
DOCKER_BUILDKIT=0 podman build --target openai-service-production -t lbob-openai:latest .
DOCKER_BUILDKIT=0 podman build -f Dockerfile.daprd -t lbob-daprd:latest .
```

### Deploying

```bash
# Set secrets
export TELEGRAM_BOT_TOKEN="your-bot-token"
export ANTHROPIC_AUTH_TOKEN="your-anthropic-proxy-token"

# Start the production stack
podman-compose --profile production up -d

# If containers show as "Created" but not "Up" (compose timeout on health checks):
podman start lbob-telegram lbob-openai
podman start lbob-telegram-dapr lbob-openai-dapr
```

### Verifying

```bash
# All 6 containers should show "Up":
podman ps --filter "name=lbob" --format "table {{.Names}}\t{{.Status}}"

# Expected:
#   lbob-redis           Up
#   lbob-loki            Up
#   lbob-telegram        Up
#   lbob-openai          Up
#   lbob-telegram-dapr   Up
#   lbob-openai-dapr     Up

# Check Dapr subscriptions loaded:
podman logs lbob-openai-dapr 2>&1 | grep "subscribed"
# Should show: app is subscribed to the following topics: [[messages]]

podman logs lbob-telegram-dapr 2>&1 | grep "subscribed"
# Should show: app is subscribed to the following topics: [[responses]]

# Check bot is polling Telegram:
podman logs lbob-telegram 2>&1 | grep "getupdates"
```

### E2E Smoke Test

Publish a test message directly to Dapr pubsub:

```bash
podman exec lbob-openai python -c "
import json, urllib.request
data = json.dumps({'chat_id': YOUR_TELEGRAM_CHAT_ID, 'text': 'What is suffering?'}).encode()
req = urllib.request.Request(
    'http://localhost:3500/v1.0/publish/redis-pubsub/messages',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
resp = urllib.request.urlopen(req)
print(f'Status: {resp.status}')
"
```

Expected: Status 204, then a response from @LittleBitsOfBuddhaBot in your Telegram chat within ~10 seconds.

### Health Check

```bash
bash scripts/lbob-healthcheck.sh
```

Checks: bot token validity (Telegram `getMe`), Redis connectivity, Dapr sidecar health, Anthropic proxy reachability.

### Stopping

```bash
podman-compose --profile production down
```

### Logs

```bash
# Individual service logs:
podman logs -f lbob-telegram
podman logs -f lbob-openai

# Loki (if promtail is running):
# Logs are shipped to lbob-loki:3100
```

## Development

### Quick Start (devcontainer)

```bash
devbox shell
dapr init --slim
podman-compose up -d redis
dapr run -f dapr.yaml
```

### Project Structure

```
.
├── src/
│   ├── telegram_bot_service_worldofgeese/   # Telegram bot (triogram + FastAPI)
│   └── openai_service_worldofgeese/         # LLM service (httpx + FastAPI)
├── .dapr/
│   └── components/
│       └── redis-pubsub.yaml                # Dapr pubsub component
├── monitoring/
│   └── promtail-config.yaml                 # Log shipping config
├── scripts/
│   └── lbob-healthcheck.sh                  # Health check script
├── Dockerfile                               # Multi-stage: telegram + openai services
├── Dockerfile.daprd                         # Dapr sidecar with baked-in components
├── compose.yaml                             # Production + dev profiles
└── docs/adr/                                # Architecture Decision Records
```

### Running Tests

```bash
devbox run -- pytest -v
```

### Known Issues

- **`ty check` reports 4 `call-non-callable` errors** on `trio.TASK_STATUS_IGNORED` — these are false positives from trio's type stubs. Pre-commit hook is bypassed with `--no-verify` for now.
- **Compose `up -d` may exit 130** before all containers start (health check timeout). Workaround: `podman start` individual containers after compose creates them.
- **Rootless Podman bind mounts** can appear empty inside containers. Dapr components are baked into the daprd image (`Dockerfile.daprd`) instead of bind-mounted.
- **triogram pins `trio==0.22.*`** which conflicts with anyio 4.x. We install triogram with `--no-deps` and pin `trio>=0.25.0` separately.

## Why Not LiteLLM?

Anthropic proxy (the Bedrock proxy for Anthropic models) requires `Authorization: Bearer <token>` as the sole auth header. LiteLLM's `anthropic/` provider always injects an `x-api-key` header alongside `Authorization`, causing Anthropic proxy to return 500. No LiteLLM configuration (`api_key=None`, `drop_params`, `extra_headers`) suppresses this. We use raw `httpx` instead.

## Architecture Decision Records

See [docs/adr/](docs/adr/) for historical decisions:

- [ADR 0001](docs/adr/0001-fix-secret-initialization-race-condition.md) — Fix secret initialization race condition
- [ADR 0002](docs/adr/0002-replace-azure-keyvault-with-local-secrets.md) — Replace Azure Key Vault with local secrets
- [ADR 0003](docs/adr/0003-replace-scaleway-redis-with-local.md) — Replace Scaleway Redis with local Redis
- [ADR 0004](docs/adr/0004-remove-garden-for-forgejo-actions.md) — Remove Garden.io for Forgejo Actions
- [ADR 0005](docs/adr/0005-remove-kubernetes-loft-pulumi.md) — Remove Kubernetes, Loft, Pulumi
- [ADR 0006](docs/adr/0006-add-podman-compose.md) — Add Podman Compose
- [ADR 0007](docs/adr/0007-add-forgejo-actions-ci.md) — Add Forgejo Actions CI

## Built With

- Python 3.11 (`python:3.11-slim`)
- [FastAPI](https://fastapi.tiangolo.com/) + [Hypercorn](https://github.com/pgjones/hypercorn) (Trio worker)
- [Triogram](https://github.com/worldofgeese/triogram) — Trio-based Telegram bot library
- [httpx](https://www.python-httpx.org/) — HTTP client for LLM calls
- [Dapr](https://dapr.io/) 1.14.4 — Distributed application runtime
- [Redis](https://redis.io/) 7 — Pub/sub message broker

## License

AGPL-3.0+
