#!/bin/bash
set -euo pipefail

# Kubernetes Manifest Deployment Script
# Applies Kustomize overlays to AKS.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="${SCRIPT_DIR}/../k8s"

ENVIRONMENT="${1:-dev}"
OVERLAY="${K8S_DIR}/overlays/${ENVIRONMENT}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Kubernetes Manifest Deployment ===${NC}"
echo "  Environment: ${ENVIRONMENT}"
echo "  Overlay: ${OVERLAY}"
echo ""

# Verify kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl not found. Install from https://kubernetes.io/docs/tasks/tools/${NC}"
    exit 1
fi

# Verify kustomize
if ! command -v kustomize &> /dev/null; then
    echo -e "${YELLOW}Warning: kustomize not found. Using kubectl built-in kustomize.${NC}"
    KUSTOMIZE="kubectl apply -k"
else
    KUSTOMIZE="kustomize build ${OVERLAY} | kubectl apply -f -"
fi

# Validate overlay exists
if [ ! -d "${OVERLAY}" ]; then
    echo -e "${RED}Error: Overlay directory not found: ${OVERLAY}${NC}"
    exit 1
fi

# Show diff
echo -e "${GREEN}Previewing changes...${NC}"
kustomize build "${OVERLAY}" | kubectl diff -f - || true

echo ""
read -p "Apply changes? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Aborted.${NC}"
    exit 0
fi

# Apply manifests
echo -e "${GREEN}Applying manifests...${NC}"
kustomize build "${OVERLAY}" | kubectl apply -f -

# Wait for rollouts
echo -e "${GREEN}Waiting for rollouts...${NC}"
kubectl rollout status deployment/${ENVIRONMENT}-agent-controller -n voice-agent --timeout=300s || true
kubectl rollout status deployment/${ENVIRONMENT}-stt-service -n voice-agent --timeout=300s || true
kubectl rollout status deployment/${ENVIRONMENT}-tts-service -n voice-agent --timeout=300s || true

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Check status:"
echo "  kubectl get pods -n voice-agent"
echo "  kubectl get svc -n voice-agent"
echo "  kubectl get ingress -n voice-agent"
