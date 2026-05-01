#!/bin/bash
set -euo pipefail

# Local Development Environment Setup
# Spins up Redis, Qdrant, and Azurite in Docker for local dev.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Local Development Environment Setup ===${NC}"
echo ""

# Verify Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker not found. Install from https://docs.docker.com/get-docker/${NC}"
    exit 1
fi

# Start local services
echo -e "${GREEN}Starting local services...${NC}"

# Redis (session state + cache)
docker run -d \
    --name voice-redis \
    --restart unless-stopped \
    -p 6379:6379 \
    redis:7-alpine \
    redis-server --appendonly yes \
    || echo "Redis already running"

# Qdrant (vector DB for RAG fallback)
docker run -d \
    --name voice-qdrant \
    --restart unless-stopped \
    -p 6333:6333 \
    -v "${PROJECT_ROOT}/.local/qdrant:/qdrant/storage" \
    qdrant/qdrant:latest \
    || echo "Qdrant already running"

# Azurite (Azure Blob Storage emulator)
docker run -d \
    --name voice-azurite \
    --restart unless-stopped \
    -p 10000:10000 \
    -v "${PROJECT_ROOT}/.local/azurite:/data" \
    mcr.microsoft.com/azure-storage/azurite:latest \
    azurite-blob --blobHost 0.0.0.0 --blobPort 10000 \
    || echo "Azurite already running"

echo ""
echo -e "${GREEN}=== Local Services ===${NC}"
echo "  Redis:     redis://localhost:6379"
echo "  Qdrant:    http://localhost:6333"
echo "  Azurite:   http://localhost:10000 (Blob)"
echo ""
echo "Environment variables for local dev:"
echo "  export REDIS_HOST=localhost"
echo "  export REDIS_PORT=6379"
echo "  export REDIS_KEY=''"
echo "  export REDIS_SSL=false"
echo "  export SEARCH_ENDPOINT=http://localhost:6333"
echo "  export SEARCH_KEY=''"
echo "  export STORAGE_CONNECTION_STRING='DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;'"
echo ""
echo -e "${YELLOW}Note: Azure OpenAI and Twilio credentials must be set manually.${NC}"
