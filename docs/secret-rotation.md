# Secret Rotation

## Overview

LBOB requires two secrets at runtime:

| Secret | Env Var | Source | Rotation |
|--------|---------|--------|----------|
| Telegram bot token | `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → `/revoke` | Revoke old, create new |
| LEGO MPS auth token | `ANTHROPIC_AUTH_TOKEN` | LEGO internal portal | Generate new token |

## Production: Environment File

Secrets are injected via an env file, **not** baked into images or compose.

```bash
# On the deploy host (e.g., Paphos):
~/.config/containers/systemd/openclaw.env
```

File format:
```
TELEGRAM_BOT_TOKEN=6014356103:AAF...
ANTHROPIC_AUTH_TOKEN=6a7f7bb5...:5ltY...
```

Permissions:
```bash
chmod 600 ~/.config/containers/systemd/openclaw.env
```

## Rotation Procedure

```bash
# 1. Generate new tokens (manual step — cannot be automated)
#    - Telegram: message @BotFather, /revoke, then /token
#    - LEGO MPS: generate new token in portal

# 2. Update the env file
bash scripts/rotate-secrets.sh

# 3. Restart services to pick up new tokens
podman-compose --profile production restart lbob-telegram lbob-openai

# 4. Verify
bash scripts/lbob-healthcheck.sh
```

## CI Secrets

For Forgejo Actions E2E tests, add secrets in the repo settings:
- Repository → Settings → Actions Secrets
- Add `TELEGRAM_BOT_TOKEN` (use a **test bot** token, not production)
- Add `ANTHROPIC_AUTH_TOKEN`

## Future: agenix Integration

For NixOS hosts (Paphos), secrets can be managed via agenix:

```nix
# In your NixOS flake:
age.secrets.lbob-telegram-token = {
  file = ./secrets/lbob-telegram-token.age;
  owner = "kypris";
};
age.secrets.lbob-anthropic-token = {
  file = ./secrets/lbob-anthropic-token.age;
  owner = "kypris";
};
```

Then reference in a systemd unit or compose env file:
```bash
TELEGRAM_BOT_TOKEN=$(cat /run/agenix/lbob-telegram-token)
ANTHROPIC_AUTH_TOKEN=$(cat /run/agenix/lbob-anthropic-token)
```

This is the recommended long-term path for Paphos deployments.
