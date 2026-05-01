#!/bin/bash
set -euo pipefail

# Azure Infrastructure Deployment Script
# Deploys Bicep templates to provision all Azure resources.
# Ref: Microsoft (2024). Azure CLI deployment docs.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="${SCRIPT_DIR}/../infrastructure/azure"

ENVIRONMENT="${1:-prod}"
LOCATION="${2:-eastus}"
RESOURCE_GROUP="rg-voice-${ENVIRONMENT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Azure Voice Agent Infrastructure Deployment ===${NC}"
echo "  Environment: ${ENVIRONMENT}"
echo "  Location: ${LOCATION}"
echo "  Resource Group: ${RESOURCE_GROUP}"
echo ""

# Verify Azure CLI
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI not found. Install from https://aka.ms/installazurecli${NC}"
    exit 1
fi

# Verify logged in
az account show &> /dev/null || {
    echo -e "${YELLOW}Not logged in to Azure. Running az login...${NC}"
    az login
}

# Create resource group
echo -e "${GREEN}Creating resource group...${NC}"
az group create \
    --name "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --tags environment="${ENVIRONMENT}" project="voice-agent" managedBy="bicep" \
    --output none

echo -e "${GREEN}Deploying Bicep templates...${NC}"
az deployment group create \
    --resource-group "${RESOURCE_GROUP}" \
    --template-file "${INFRA_DIR}/main.bicep" \
    --parameters "${INFRA_DIR}/parameters.${ENVIRONMENT}.json" \
    --parameters location="${LOCATION}" \
    --output table

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Update secrets in Key Vault:"
echo "     az keyvault secret set --vault-name <kv-name> --name twilio-auth-token --value <token>"
echo "     az keyvault secret set --vault-name <kv-name> --name twilio-account-sid --value <sid>"
echo ""
echo "  2. Get AKS credentials:"
echo "     az aks get-credentials --resource-group ${RESOURCE_GROUP} --name aks-voice-${ENVIRONMENT}"
echo ""
echo "  3. Deploy Kubernetes manifests:"
echo "     ./scripts/deploy-k8s.sh ${ENVIRONMENT}"
