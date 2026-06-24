#!/usr/bin/env bash
# WebRTC ASR service entrypoint.
set -euo pipefail

export PYTHONPATH="/app"
export PORT="${PORT:-8000}"
export MOONSHINE_WEBRTC_ENABLED="${MOONSHINE_WEBRTC_ENABLED:-true}"
export MOONSHINE_LANGUAGE="${MOONSHINE_LANGUAGE:-en}"
export MOONSHINE_UPDATE_INTERVAL_MS="${MOONSHINE_UPDATE_INTERVAL_MS:-500}"
export RECORDINGS_DIR="${RECORDINGS_DIR:-/app/recordings}"

exec uvicorn src.api.webrtc_main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT}" \
    --workers "${UVICORN_WORKERS:-1}" \
    --log-level "${LOG_LEVEL:-info}"
