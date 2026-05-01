#!/bin/bash
set -euo pipefail

# STT Service entrypoint
# Starts faster-whisper ASR server via FastAPI.

PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo "Starting STT Service..."
echo "  Model: $MODEL_SIZE"
echo "  Compute type: $COMPUTE_TYPE"
echo "  Device: cuda"

# Verify GPU is available
python -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'; print(f'GPU: {torch.cuda.get_device_name(0)}')"

exec uvicorn src.asr.stt_server:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers 1 \
    --loop uvloop
