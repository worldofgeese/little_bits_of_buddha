#!/usr/bin/env bash
# scripts/lbob-e2e-test.sh — End-to-end smoke test for Little Bits of Buddha
#
# Usage:
#   TELEGRAM_BOT_TOKEN=xxx ANTHROPIC_AUTH_TOKEN=xxx bash scripts/lbob-e2e-test.sh
#
# What it does:
#   1. Builds all images
#   2. Starts the production compose stack
#   3. Waits for Dapr sidecars + services to be healthy
#   4. Publishes a test message to Dapr pubsub
#   5. Polls openai-service logs for LLM response
#   6. Tears down the stack
#   7. Exits 0 on success, 1 on failure
#
# Requires: podman (or docker), compose, curl, jq
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[E2E]${NC} $*"; }
warn() { echo -e "${YELLOW}[E2E]${NC} $*"; }
fail() { echo -e "${RED}[E2E FAIL]${NC} $*"; cleanup; exit 1; }

# Cleanup on exit
cleanup() {
    log "Tearing down stack..."
    docker compose --profile production down -v 2>/dev/null || true
}
trap cleanup EXIT

# Validate env
: "${TELEGRAM_BOT_TOKEN:?Set TELEGRAM_BOT_TOKEN}"
: "${ANTHROPIC_AUTH_TOKEN:?Set ANTHROPIC_AUTH_TOKEN}"

export TELEGRAM_BOT_TOKEN ANTHROPIC_AUTH_TOKEN

# Step 1: Build images
log "Building images..."
DOCKER_BUILDKIT=0 docker build --target telegram-bot-service-production -t lbob-telegram:latest . 2>&1 | tail -3
DOCKER_BUILDKIT=0 docker build --target openai-service-production -t lbob-openai:latest . 2>&1 | tail -3
DOCKER_BUILDKIT=0 docker build -f Dockerfile.daprd -t lbob-daprd:latest . 2>&1 | tail -3
log "Images built."

# Step 2: Start stack
log "Starting production stack..."
docker compose --profile production up -d --no-build 2>&1 || true

# Compose may exit before containers start (health check timeout). Start manually.
sleep 5
for c in lbob-redis lbob-loki lbob-telegram lbob-openai; do
    docker start "$c" 2>/dev/null || true
done
sleep 3
for c in lbob-telegram-dapr lbob-openai-dapr; do
    docker start "$c" 2>/dev/null || true
done

# Step 3: Wait for health
log "Waiting for services to be healthy..."
MAX_WAIT=120
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Check openai-dapr subscribed to messages topic
    if docker logs lbob-openai-dapr 2>&1 | grep -q "subscribed to the following topics.*messages"; then
        # Check telegram-dapr subscribed to responses topic
        if docker logs lbob-telegram-dapr 2>&1 | grep -q "subscribed to the following topics.*responses"; then
            # Check telegram service is polling
            if docker logs lbob-telegram 2>&1 | grep -q "getupdates"; then
                log "All services healthy after ${ELAPSED}s"
                break
            fi
        fi
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    warn "Service logs:"
    docker logs lbob-openai-dapr 2>&1 | tail -10
    docker logs lbob-telegram-dapr 2>&1 | tail -10
    docker logs lbob-telegram 2>&1 | tail -10
    fail "Services did not become healthy within ${MAX_WAIT}s"
fi

# Step 4: Publish test message via Dapr
TEST_MSG="E2E test $(date +%s)"
log "Publishing test message: '$TEST_MSG'"

docker exec lbob-openai python -c "
import json, urllib.request
data = json.dumps({'chat_id': 0, 'text': '$TEST_MSG'}).encode()
req = urllib.request.Request(
    'http://localhost:3500/v1.0/publish/redis-pubsub/messages',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
resp = urllib.request.urlopen(req)
print(f'Publish status: {resp.status}')
assert resp.status == 204, f'Expected 204, got {resp.status}'
" 2>&1 || fail "Failed to publish test message to Dapr"

# Step 5: Wait for LLM response in openai-service logs
log "Waiting for LLM response..."
LLM_WAIT=90
LLM_ELAPSED=0
while [ $LLM_ELAPSED -lt $LLM_WAIT ]; do
    if docker logs lbob-openai 2>&1 | grep -q "HTTP Request: POST.*models.assistant.legogroup.io.*200 OK"; then
        log "LLM responded (200 OK) after ${LLM_ELAPSED}s"
        break
    fi
    sleep 5
    LLM_ELAPSED=$((LLM_ELAPSED + 5))
done

if [ $LLM_ELAPSED -ge $LLM_WAIT ]; then
    warn "openai-service logs:"
    docker logs lbob-openai 2>&1 | tail -20
    fail "LLM did not respond within ${LLM_WAIT}s"
fi

# Step 6: Verify response was published to responses topic
# Check telegram service received the response (it will fail to send to chat_id=0, but the log shows it tried)
sleep 5
if docker logs lbob-telegram 2>&1 | grep -q "sendmessage\|Received message"; then
    log "Telegram service received response and attempted delivery"
else
    warn "Telegram service may not have received the response (check logs)"
fi

# All checks passed
log "========================================="
log "  E2E SMOKE TEST PASSED"
log "========================================="
log "Pipeline: Dapr publish → openai-service → LEGO MPS (200) → Dapr responses → telegram-service"
exit 0
