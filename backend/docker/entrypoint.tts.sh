#!/bin/bash
set -euo pipefail

# TTS Service entrypoint
# Starts Piper TTS server via FastAPI.

PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo "Starting TTS Service..."
echo "  Voice: $PIPER_VOICE_NAME"
echo "  Voice dir: $PIPER_VOICE_DIR"

exec uvicorn src.tts.tts_server:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers 1 \
    --loop uvloop
