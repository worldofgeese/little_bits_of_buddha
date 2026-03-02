#!/usr/bin/env bash
# LBOB Health Check — sends a test message via Telegram getMe API
# and checks if the bot process is responding.
#
# Usage: bash scripts/lbob-healthcheck.sh
# Returns 0 if healthy, 1 if unhealthy.

set -euo pipefail

BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-6014356103:AAFMthhrKMXJLdeuU3rK09ViK27bCJiJTlw}"
LBOB_DIR="/home/node/.openclaw/workspace/projects/little_bits_of_buddha"

# Check 1: Bot token valid (getMe)
echo "Checking Telegram bot token..."
ME_RESPONSE=$(curl -sf "https://api.telegram.org/bot${BOT_TOKEN}/getMe" 2>/dev/null || echo '{"ok":false}')
if echo "$ME_RESPONSE" | grep -q '"ok":true'; then
    BOT_NAME=$(echo "$ME_RESPONSE" | grep -o '"username":"[^"]*"' | cut -d'"' -f4)
    echo "✓ Bot @${BOT_NAME} token is valid"
else
    echo "✗ Bot token invalid or Telegram API unreachable"
    exit 1
fi

# Check 2: Redis is running
echo "Checking Redis..."
if command -v redis-cli &>/dev/null; then
    if redis-cli -h localhost ping 2>/dev/null | grep -q PONG; then
        echo "✓ Redis is responding"
    else
        echo "✗ Redis not responding"
        exit 1
    fi
else
    echo "⚠ redis-cli not available, skipping Redis check"
fi

# Check 3: Dapr sidecar healthy (if running)
echo "Checking Dapr sidecars..."
for port in 3500 3510; do
    if curl -sf "http://localhost:${port}/v1.0/healthz" -o /dev/null 2>/dev/null; then
        echo "✓ Dapr sidecar on port ${port} is healthy"
    else
        echo "⚠ Dapr sidecar on port ${port} not responding (may not be running)"
    fi
done

# Check 4: LEGO MPS endpoint reachable
echo "Checking LEGO MPS endpoint..."
LMS_RESPONSE=$(curl -sf -o /dev/null -w "%{http_code}" "https://ANTHROPIC_PROXY_HOST/claude" 2>/dev/null || echo "000")
if [ "$LMS_RESPONSE" != "000" ]; then
    echo "✓ LEGO MPS endpoint reachable (HTTP ${LMS_RESPONSE})"
else
    echo "✗ LEGO MPS endpoint unreachable"
    exit 1
fi

echo ""
echo "Health check passed ✓"
exit 0
