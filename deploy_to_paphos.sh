#!/bin/bash
# Deploy Buddha Bot Service to Paphos
#
# This script deploys the simplified single-service architecture to Paphos

set -e

# Configuration
SSH_KEY="${HOME}/.ssh/id_ed25519_paphos"
PAPHOS_HOST="kypris@192.168.99.104"
PROJECT_PATH="/home/kypris/little_bits_of_buddha"
CONTAINER_NAME="lbob-simplified"

echo "=== Buddha Bot Service Deployment ==="
echo ""

# Step 1: Pull latest code
echo "[1/5] Pulling latest code from Forgejo..."
ssh -i "$SSH_KEY" "$PAPHOS_HOST" "cd $PROJECT_PATH && git pull origin main"

# Step 2: Copy environment file if exists locally
echo "[2/5] Checking environment configuration..."
if [ -f ".env" ]; then
    echo "  Copying .env to Paphos..."
    scp -i "$SSH_KEY" .env "$PAPHOS_HOST:$PROJECT_PATH/.env"
else
    echo "  WARNING: .env file not found locally. Ensure it's configured on Paphos."
fi

# Step 3: Build and restart container
echo "[3/5] Building and restarting container..."
ssh -i "$SSH_KEY" "$PAPHOS_HOST" "cd $PROJECT_PATH && podman-compose -f compose.simplified.yaml down"
ssh -i "$SSH_KEY" "$PAPHOS_HOST" "cd $PROJECT_PATH && podman-compose -f compose.simplified.yaml up -d --build"

# Step 4: Verify service health
echo "[4/5] Verifying service health..."
sleep 5
HEALTH=$(curl -s http://localhost:8080/health 2>/dev/null || echo '{"status":"unknown"}')
echo "  Health check: $HEALTH"

# Step 5: Set webhook
echo "[5/5] Telegram webhook configuration..."
ssh -i "$SSH_KEY" "$PAPHOS_HOST" "
    TOKEN=\$(grep TELEGRAM_BOT_TOKEN $PROJECT_PATH/.env | cut -d'=' -f2)
    echo '  Setting webhook to: https://paphos.hound-celsius.ts.net/webhook'
    curl -s -X POST "https://api.telegram.org/bot\$TOKEN/setWebhook" \
        -H "Content-Type: application/json" \
        -d '{"url": "https://paphos.hound-celsius.ts.net/webhook"}'
"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Service URL: http://localhost:8080"
echo "Webhook: https://paphos.hound-celsius.ts.net/webhook"
echo "Logs: podman logs $CONTAINER_NAME"
