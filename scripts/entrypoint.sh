#!/bin/bash
# Entrypoint wrapper: index suttas on startup, then run the app.
# Sutta indexing runs in background to not block app startup.
set -e

# Index suttas if corpus exists and Redis is reachable
if [ -f /app/sutta_corpus/suttas.json ]; then
    echo "Indexing suttas in background..."
    (
        # Wait for Redis to be ready (max 30s)
        for i in $(seq 1 30); do
            python -c "import redis; r=redis.Redis(host='${REDIS_HOST:-localhost}'); r.ping()" 2>/dev/null && break
            sleep 1
        done
        python /app/embed_suttas.py --corpus-path /app/sutta_corpus/suttas.json 2>&1 | tail -3
    ) &
fi

# Run the actual app
exec python -m openai_service_worldofgeese "$@"
