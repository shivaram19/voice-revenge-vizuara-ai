#!/bin/bash
set -euo pipefail

# Agent Controller entrypoint
# Starts FastAPI with Uvicorn workers tuned for WebSocket concurrency.
# Ref: Uvicorn deployment guide. 1 worker per CPU core, minimum 2.

WORKERS=${UVICORN_WORKERS:-2}
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

# Force unbuffered stdout/stderr — Container App log driver only sees lines
# the process actually flushes. With multi-worker uvicorn + structlog writing
# JSON via stdlib logging → StreamHandler, block-buffering on a pipe causes
# our structured app events (stt_final, llm_response, barge_in_*, filler_*)
# to never reach Log Analytics. PYTHONUNBUFFERED=1 disables Python-side
# buffering globally. DFS-007 §6 / ADR-013 instrumentation requirement.
export PYTHONUNBUFFERED=1

echo "Starting Agent Controller..."
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Workers: $WORKERS"
echo "  PYTHONUNBUFFERED: $PYTHONUNBUFFERED"

exec uvicorn src.api.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --loop uvloop \
    --http h11 \
    --ws websockets \
    --proxy-headers \
    --forwarded-allow-ips '*'
