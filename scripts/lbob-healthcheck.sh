#!/usr/bin/env bash
# LBOB Health Check — checks container health via podman-in-podman
# Usage: bash scripts/lbob-healthcheck.sh
# Returns 0 if healthy, 1 if unhealthy. Outputs human-readable status.

set -euo pipefail

export DOCKER_HOST="${DOCKER_HOST:-tcp://podman-in-podman:2375}"
ALERT_FILE="${HOME}/.openclaw/workspace/memory/lbob-health-alert.txt"

FAILED=0
STATUS=""

check() {
    local name="$1" cmd="$2"
    if eval "$cmd" &>/dev/null; then
        STATUS="${STATUS}✓ ${name}\n"
    else
        STATUS="${STATUS}✗ ${name}\n"
        FAILED=1
    fi
}

# Check all 5 core containers are running
for c in lbob-redis lbob-telegram lbob-telegram-dapr lbob-openai lbob-openai-dapr; do
    check "$c running" "docker inspect -f '{{.State.Running}}' $c 2>/dev/null | grep -q true"
done

# Check Telegram bot token is valid
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-6014356103:AAFMthhrKMXJLdeuU3rK09ViK27bCJiJTlw}"
check "Bot token valid" "curl -sf 'https://api.telegram.org/bot${BOT_TOKEN}/getMe' | grep -q '\"ok\":true'"

# Check Anthropic proxy reachable
check "Anthropic proxy reachable" "curl -sf -o /dev/null -w '%{http_code}' 'https://ANTHROPIC_PROXY_HOST/claude' | grep -qv 000"

# Check Redis has sutta index
check "Sutta index exists" "docker exec lbob-redis redis-cli FT.INFO sutta_idx 2>/dev/null | grep -q sutta_idx"

# Check Dapr subscriptions active (openai service)
check "Dapr subscriptions" "docker exec lbob-openai-dapr wget -qO- http://localhost:3500/v1.0/healthz 2>/dev/null"

# Check for recent errors in openai service logs (last 5 min)
ERRORS=$(docker logs lbob-openai --since 5m 2>&1 | grep -ci "error\|traceback\|exception" || true)
if [ "$ERRORS" -gt 3 ]; then
    STATUS="${STATUS}⚠ ${ERRORS} errors in last 5min logs\n"
    FAILED=1
else
    STATUS="${STATUS}✓ Logs clean (${ERRORS} errors)\n"
fi

echo -e "$STATUS"

if [ "$FAILED" -eq 1 ]; then
    echo -e "LBOB_UNHEALTHY\n$(date -Iseconds)\n${STATUS}" > "$ALERT_FILE"
    echo "LBOB_UNHEALTHY"
    exit 1
else
    # Clear any previous alert
    rm -f "$ALERT_FILE"
    echo "LBOB_HEALTHY"
    exit 0
fi
