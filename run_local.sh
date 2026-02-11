#!/bin/bash
# Run Buddha Bot Service locally for testing

set -e

# Set environment variables (override these in production)
export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-6014356103:AAFMthhrKMXJLdeuU3rK09ViK27bCJiJTlw}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-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}"
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8080}"

echo "Starting Little Bits of Buddha Bot Service..."
echo "  TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:0:10}..."
echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..."
echo "  HOST: $HOST"
echo "  PORT: $PORT"
echo ""

cd "$(dirname "$0")"

# Activate virtual environment and run
source .venv/bin/activate

echo "Running service..."
python -m buddha_bot_service
