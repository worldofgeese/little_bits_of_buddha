#!/usr/bin/env bash
# scripts/rotate-secrets.sh — Interactive secret rotation for LBOB
#
# Usage: bash scripts/rotate-secrets.sh
#
# Prompts for new token values and writes them to the env file.
# Does NOT restart services — do that after running this script.
set -euo pipefail

ENV_FILE="${LBOB_ENV_FILE:-$HOME/.config/containers/systemd/openclaw.env}"

echo "=== LBOB Secret Rotation ==="
echo "Env file: $ENV_FILE"
echo ""

# Backup existing
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "${ENV_FILE}.bak.$(date +%Y%m%d%H%M%S)"
    echo "Backed up existing env file."
fi

# Read current values (for display, masked)
if [ -f "$ENV_FILE" ]; then
    CURRENT_TG=$(grep "^TELEGRAM_BOT_TOKEN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || echo "")
    CURRENT_AT=$(grep "^ANTHROPIC_AUTH_TOKEN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || echo "")
    if [ -n "$CURRENT_TG" ]; then
        echo "Current Telegram token: ${CURRENT_TG:0:10}...${CURRENT_TG: -4}"
    fi
    if [ -n "$CURRENT_AT" ]; then
        echo "Current Anthropic token: ${CURRENT_AT:0:10}...${CURRENT_AT: -4}"
    fi
    echo ""
fi

# Prompt for new values
read -rp "New TELEGRAM_BOT_TOKEN (or Enter to keep current): " NEW_TG
read -rp "New ANTHROPIC_AUTH_TOKEN (or Enter to keep current): " NEW_AT

# Use current values as fallback
TG="${NEW_TG:-${CURRENT_TG:-}}"
AT="${NEW_AT:-${CURRENT_AT:-}}"

if [ -z "$TG" ] || [ -z "$AT" ]; then
    echo "ERROR: Both tokens must be set."
    exit 1
fi

# Write env file
mkdir -p "$(dirname "$ENV_FILE")"
cat > "$ENV_FILE" <<EOF
TELEGRAM_BOT_TOKEN=$TG
ANTHROPIC_AUTH_TOKEN=$AT
EOF

chmod 600 "$ENV_FILE"
echo ""
echo "✅ Secrets written to $ENV_FILE (mode 600)"
echo ""
echo "Next steps:"
echo "  1. Restart services: podman-compose --profile production restart lbob-telegram lbob-openai"
echo "  2. Verify: bash scripts/lbob-healthcheck.sh"
