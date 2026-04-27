#!/bin/bash
set -euo pipefail

# Agent Controller entrypoint
# Starts FastAPI with Uvicorn workers tuned for WebSocket concurrency.
# Ref: Uvicorn deployment guide. 1 worker per CPU core, minimum 2.

WORKERS=${UVICORN_WORKERS:-2}
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo "Starting Agent Controller..."
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Workers: $WORKERS"

exec uvicorn src.api.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --loop uvloop \
    --http h11 \
    --ws websockets \
    --proxy-headers \
    --forwarded-allow-ips '*'
