# Little Bits of Buddha

<figure>
  <img src="https://us-east-1.linodeobjects.com/kinopio-uploads/wvF4LRNvUWaQyrINvklmE/little-bits-of-buddha-telegram-bot-logo--SNM.jpg" alt="A robotic monk with a wheel-maze for a head against a blue field" width="250" />
</figure>

A Telegram bot that speaks as the Buddha, responding to users with teachings in the style of the Early Buddhist Canon.

**Try it:** [@LittleBitsOfBuddhaBot](https://t.me/LittleBitsOfBuddhaBot)

## Architecture

This project demonstrates a microservices architecture using [Dapr](https://dapr.io/) for service-to-service communication.

```
┌─────────────────┐     pub/sub      ┌─────────────────┐
│  Telegram Bot   │ ───────────────► │  OpenAI Service │
│    Service      │ ◄─────────────── │                 │
└─────────────────┘    (Redis)       └─────────────────┘
        │                                     │
        ▼                                     ▼
   Telegram API                         OpenAI GPT-5.2
```

**Services:**
- `telegram-bot-service` — Receives messages from Telegram, publishes to Dapr pub/sub, sends responses back to users
- `openai-service` — Subscribes to messages, generates responses using GPT-5.2 with a Buddha persona

**Infrastructure:**
- [Dapr](https://dapr.io/) — Pub/sub messaging, secrets management
- [Redis](https://redis.io/) — Message broker for Dapr pub/sub
- [Podman](https://podman.io/) — Container runtime (rootless)

## Quick Start

### Prerequisites

- [Devbox](https://www.jetpack.io/devbox/) — `curl -fsSL https://get.jetpack.io/devbox | bash`
- [Dapr CLI](https://docs.dapr.io/getting-started/install-dapr-cli/) — `curl -fsSL https://raw.githubusercontent.com/dapr/cli/master/install/install.sh | bash`
- [Podman](https://podman.io/) or Docker

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://paphos.hound-celsius.ts.net/kypris/little_bits_of_buddha.git
   cd little_bits_of_buddha
   ```

2. **Enter the development environment:**
   ```bash
   devbox shell
   ```

3. **Configure secrets:**
   ```bash
   cp secrets/secrets.json.example secrets/secrets.json
   # Edit secrets/secrets.json with your actual tokens:
   # - telegram-secret: Your Telegram bot token from @BotFather
   # - openai-secret: Your OpenAI API key
   ```

4. **Start Redis:**
   ```bash
   podman-compose up -d redis
   ```

5. **Initialize Dapr:**
   ```bash
   dapr init --slim
   ```

6. **Run the services:**
   ```bash
   dapr run -f dapr.yaml
   ```

The bot should now be responding to messages!

## Development

### Project Structure

```
.
├── src/
│   ├── telegram_bot_service_worldofgeese/   # Telegram bot service
│   └── openai_service_worldofgeese/         # OpenAI/LLM service
├── .dapr/
│   └── components/                          # Dapr component configs
├── secrets/                                 # Local secrets (gitignored)
├── docs/
│   └── adr/                                 # Architecture Decision Records
├── dapr.yaml                                # Dapr multi-app config
└── compose.yaml                             # Podman Compose config
```

### Running Tests

```bash
devbox run -- pytest -v
```

### Type Checking

```bash
devbox run -- pyright src/
```

### Local CI Testing

Test the CI workflow locally using Forgejo runner:

```bash
forgejo-runner exec --image -self-hosted
```

## Deployment

For production deployment, use the full containerized stack:

```bash
podman-compose --profile production up -d
```

This starts Redis and both services as containers.

## Architecture Decision Records

See [docs/adr/](docs/adr/) for architectural decisions:

- [ADR 0001](docs/adr/0001-fix-secret-initialization-race-condition.md) — Fix secret initialization race condition
- [ADR 0002](docs/adr/0002-replace-azure-keyvault-with-local-secrets.md) — Replace Azure Key Vault with local secrets
- [ADR 0003](docs/adr/0003-replace-scaleway-redis-with-local.md) — Replace Scaleway Redis with local Redis
- [ADR 0004](docs/adr/0004-remove-garden-for-forgejo-actions.md) — Remove Garden.io for Forgejo Actions
- [ADR 0005](docs/adr/0005-remove-kubernetes-loft-pulumi.md) — Remove Kubernetes, Loft, Pulumi
- [ADR 0006](docs/adr/0006-add-podman-compose.md) — Add Podman Compose
- [ADR 0007](docs/adr/0007-add-forgejo-actions-ci.md) — Add Forgejo Actions CI

## Built With

- Python 3.11
- [FastAPI](https://fastapi.tiangolo.com/) — Async web framework
- [Triogram](https://github.com/worldofgeese/triogram) — Trio-based Telegram bot library
- [Dapr](https://dapr.io/) — Distributed application runtime
- [PDM](https://pdm.fming.dev/) — Python package manager
- [Devbox](https://www.jetpack.io/devbox/) — Reproducible development environments

## License

AGPL-3.0+
