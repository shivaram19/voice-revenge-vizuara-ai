#!/bin/bash
set -euo pipefail

# =============================================================================
# Construction Receptionist — Azure Deployment Script
# =============================================================================
# Deploys the construction-specialized AI receptionist to Azure.
#
# Architecture:
#   - Azure Container Apps (recommended) OR Azure Kubernetes Service (AKS)
#   - Azure Container Registry (ACR)
#   - Azure OpenAI Service (gpt-4o-mini)
#   - Azure Cache for Redis (session state)
#   - Azure Key Vault (secrets)
#   - Application Insights (monitoring)
#
# Scale: 10-50 concurrent calls. No GPU. Cloud APIs only.
# Backend: SQLite (file-based, mounted as container volume).
#
# Prerequisites:
#   - Azure CLI (az) installed and logged in
#   - Docker installed and running
#   - kubectl installed (only for AKS target)
#   - Twilio account with phone number configured
#
# Usage:
#   ./deploy-construction.sh [target] [environment] [location]
#
# Targets:
#   aca   — Azure Container Apps (default, simpler, cheaper)
#   aks   — Azure Kubernetes Service (existing cluster)
#
# Examples:
#   ./deploy-construction.sh aca prod eastus
#   ./deploy-construction.sh aks prod eastus
#
# Ref: Microsoft (2024). Azure Well-Architected Framework [^44].
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."
INFRA_DIR="${PROJECT_DIR}/infrastructure/azure"
K8S_DIR="${PROJECT_DIR}/k8s/construction"

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------
TARGET="${1:-aca}"        # aca | aks
ENVIRONMENT="${2:-prod}"
LOCATION="${3:-eastus}"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RESOURCE_GROUP="rg-buildpro-${ENVIRONMENT}"
BASE_NAME="buildpro-${ENVIRONMENT}"
ACR_NAME="${BASE_NAME}acr"
IMAGE_NAME="construction-receptionist"
IMAGE_TAG="${ENVIRONMENT}-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')"

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ---------------------------------------------------------------------------
# Phase 0: Prerequisites
# ---------------------------------------------------------------------------

check_prerequisites() {
    log_step "Phase 0: Checking Prerequisites"

    # Azure CLI
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI not found. Install: https://aka.ms/installazurecli"
        exit 1
    fi
    log_info "Azure CLI: $(az --version | head -1)"

    # Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Install: https://docs.docker.com/get-docker/"
        exit 1
    fi
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Start Docker Desktop."
        exit 1
    fi
    log_info "Docker: $(docker --version)"

    # kubectl (only for AKS)
    if [[ "$TARGET" == "aks" ]]; then
        if ! command -v kubectl &> /dev/null; then
            log_error "kubectl not found. Install: https://kubernetes.io/docs/tasks/tools/"
            exit 1
        fi
        log_info "kubectl: $(kubectl version --client 2>/dev/null | head -1 || echo 'installed')"
    fi

    # Azure login
    if ! az account show &> /dev/null; then
        log_warn "Not logged in to Azure. Running az login..."
        az login
    fi
    local account
    account=$(az account show --query "name" -o tsv)
    log_info "Azure subscription: ${account}"

    # Validate target
    if [[ "$TARGET" != "aca" && "$TARGET" != "aks" ]]; then
        log_error "Invalid target: ${TARGET}. Use 'aca' or 'aks'."
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Phase 1: Build Container Image
# ---------------------------------------------------------------------------

build_image() {
    log_step "Phase 1: Building Container Image"

    local full_image_name="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"

    log_info "Building: ${full_image_name}"
    log_info "Dockerfile: docker/Dockerfile.agent"

    docker build \
        --platform linux/amd64 \
        -t "${full_image_name}" \
        -f "${PROJECT_DIR}/docker/Dockerfile.agent" \
        "${PROJECT_DIR}"

    log_info "Image built successfully."
}

# ---------------------------------------------------------------------------
# Phase 2: Provision Azure Infrastructure
# ---------------------------------------------------------------------------

provision_infrastructure() {
    log_step "Phase 2: Provisioning Azure Infrastructure"

    log_info "Resource Group: ${RESOURCE_GROUP}"
    log_info "Location: ${LOCATION}"
    log_info "Target: ${TARGET}"

    # Create resource group
    az group create \
        --name "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --tags environment="${ENVIRONMENT}" project="construction-receptionist" managedBy="bicep" \
        --output none
    log_info "Resource group ready."

    if [[ "$TARGET" == "aca" ]]; then
        # Deploy Container Apps infrastructure
        log_info "Deploying Bicep: main-construction.bicep"
        az deployment group create \
            --resource-group "${RESOURCE_GROUP}" \
            --template-file "${INFRA_DIR}/main-construction.bicep" \
            --parameters "${INFRA_DIR}/parameters.construction.json" \
            --parameters environment="${ENVIRONMENT}" \
            --output table
    else
        # Deploy standard AKS infrastructure
        log_info "Deploying Bicep: main.bicep"
        az deployment group create \
            --resource-group "${RESOURCE_GROUP}" \
            --template-file "${INFRA_DIR}/main.bicep" \
            --parameters "${INFRA_DIR}/parameters.${ENVIRONMENT}.json" \
            --parameters environment="${ENVIRONMENT}" \
            --output table
    fi

    log_info "Infrastructure provisioned."
}

# ---------------------------------------------------------------------------
# Phase 3: Push Container to ACR
# ---------------------------------------------------------------------------

push_image() {
    log_step "Phase 3: Pushing Container to ACR"

    local full_image_name="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"

    log_info "Logging in to ACR: ${ACR_NAME}"
    az acr login --name "${ACR_NAME}"

    log_info "Pushing: ${full_image_name}"
    docker push "${full_image_name}"

    # Tag as latest for convenience
    docker tag "${full_image_name}" "${ACR_NAME}.azurecr.io/${IMAGE_NAME}:latest"
    docker push "${ACR_NAME}.azurecr.io/${IMAGE_NAME}:latest"

    log_info "Image pushed successfully."
}

# ---------------------------------------------------------------------------
# Phase 4: Configure Secrets
# ---------------------------------------------------------------------------

configure_secrets() {
    log_step "Phase 4: Configuring Secrets"

    # Get outputs from deployment
    local keyvault_name
    keyvault_name=$(az deployment group show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "main-construction" \
        --query "properties.outputs.keyVaultName.value" \
        -o tsv 2>/dev/null || echo "")

    if [[ -z "$keyvault_name" ]]; then
        # Fallback: try standard main.bicep output name pattern
        keyvault_name=$(az deployment group show \
            --resource-group "${RESOURCE_GROUP}" \
            --name "main" \
            --query "properties.outputs.keyVaultName.value" \
            -o tsv 2>/dev/null || echo "")
    fi

    # Prompt for Twilio credentials if not set
    if [[ -z "${TWILIO_ACCOUNT_SID:-}" ]]; then
        log_warn "TWILIO_ACCOUNT_SID not set in environment."
        read -rp "Enter Twilio Account SID: " TWILIO_ACCOUNT_SID
    fi

    if [[ -z "${TWILIO_AUTH_TOKEN:-}" ]]; then
        log_warn "TWILIO_AUTH_TOKEN not set in environment."
        read -rsp "Enter Twilio Auth Token: " TWILIO_AUTH_TOKEN
        echo
    fi

    if [[ -z "${DEEPGRAM_API_KEY:-}" ]]; then
        log_warn "DEEPGRAM_API_KEY not set in environment."
        read -rsp "Enter Deepgram API Key: " DEEPGRAM_API_KEY
        echo
    fi

    if [[ -n "$keyvault_name" ]]; then
        log_info "Storing secrets in Key Vault: ${keyvault_name}"
        az keyvault secret set --vault-name "${keyvault_name}" --name "twilio-account-sid" --value "${TWILIO_ACCOUNT_SID}" --output none
        az keyvault secret set --vault-name "${keyvault_name}" --name "twilio-auth-token" --value "${TWILIO_AUTH_TOKEN}" --output none
        az keyvault secret set --vault-name "${keyvault_name}" --name "deepgram-api-key" --value "${DEEPGRAM_API_KEY}" --output none
        log_info "Secrets stored in Key Vault."
    else
        log_warn "Key Vault not found. Secrets must be configured manually."
    fi

    # For ACA, update container app secrets directly
    if [[ "$TARGET" == "aca" ]]; then
        local container_app_name
        container_app_name=$(az deployment group show \
            --resource-group "${RESOURCE_GROUP}" \
            --name "main-construction" \
            --query "properties.outputs.containerAppName.value" \
            -o tsv 2>/dev/null || echo "${BASE_NAME}-app")

        log_info "Updating Container App secrets: ${container_app_name}"
        az containerapp secret set \
            --name "${container_app_name}" \
            --resource-group "${RESOURCE_GROUP}" \
            --secrets \
                "twilio-account-sid=${TWILIO_ACCOUNT_SID}" \
                "twilio-auth-token=${TWILIO_AUTH_TOKEN}" \
                "deepgram-api-key=${DEEPGRAM_API_KEY}" \
            --output none

        log_info "Restarting Container App to pick up secrets..."
        az containerapp revision restart \
            --name "${container_app_name}" \
            --resource-group "${RESOURCE_GROUP}" \
            --output none
    fi
}

# ---------------------------------------------------------------------------
# Phase 5: Deploy Application
# ---------------------------------------------------------------------------

deploy_application() {
    log_step "Phase 5: Deploying Application"

    if [[ "$TARGET" == "aca" ]]; then
        deploy_aca
    else
        deploy_aks
    fi
}

deploy_aca() {
    local container_app_name
    container_app_name=$(az deployment group show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "main-construction" \
        --query "properties.outputs.containerAppName.value" \
        -o tsv 2>/dev/null || echo "${BASE_NAME}-app")

    local full_image_name="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"

    log_info "Updating Container App image: ${container_app_name}"
    az containerapp update \
        --name "${container_app_name}" \
        --resource-group "${RESOURCE_GROUP}" \
        --image "${full_image_name}" \
        --output table

    log_info "Container App updated."
}

deploy_aks() {
    local aks_name
    aks_name=$(az aks list \
        --resource-group "${RESOURCE_GROUP}" \
        --query "[0].name" -o tsv)

    if [[ -z "$aks_name" ]]; then
        log_error "AKS cluster not found in resource group ${RESOURCE_GROUP}"
        exit 1
    fi

    log_info "Getting AKS credentials: ${aks_name}"
    az aks get-credentials \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${aks_name}" \
        --overwrite-existing

    local overlay="${K8S_DIR}/overlays/${ENVIRONMENT}"
    if [[ ! -d "$overlay" ]]; then
        log_error "Kustomize overlay not found: ${overlay}"
        exit 1
    fi

    log_info "Applying Kustomize overlay: ${overlay}"

    if command -v kustomize &> /dev/null; then
        kustomize build "$overlay" | kubectl apply -f -
    else
        kubectl apply -k "$overlay"
    fi

    log_info "Waiting for rollout..."
    kubectl rollout status "deployment/${ENVIRONMENT}-construction-receptionist" \
        -n construction-receptionist --timeout=300s || true
}

# ---------------------------------------------------------------------------
# Phase 6: Verify Deployment
# ---------------------------------------------------------------------------

verify_deployment() {
    log_step "Phase 6: Verifying Deployment"

    if [[ "$TARGET" == "aca" ]]; then
        local container_app_name
        container_app_name=$(az deployment group show \
            --resource-group "${RESOURCE_GROUP}" \
            --name "main-construction" \
            --query "properties.outputs.containerAppName.value" \
            -o tsv 2>/dev/null || echo "${BASE_NAME}-app")

        local fqdn
        fqdn=$(az containerapp show \
            --name "${container_app_name}" \
            --resource-group "${RESOURCE_GROUP}" \
            --query "properties.configuration.ingress.fqdn" \
            -o tsv)

        local url="https://${fqdn}"

        log_info "Container App FQDN: ${fqdn}"
        log_info "Health endpoint: ${url}/health/live"

        # Wait a moment for the container to start
        sleep 5

        log_info "Checking health endpoint..."
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" "${url}/health/live" 2>/dev/null || echo "000")

        if [[ "$http_code" == "200" ]]; then
            log_info "Health check PASSED (HTTP 200)"
        else
            log_warn "Health check returned HTTP ${http_code}. Container may still be starting."
        fi

        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}  DEPLOYMENT COMPLETE${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo "  Target:        Azure Container Apps"
        echo "  Environment:   ${ENVIRONMENT}"
        echo "  Resource Group: ${RESOURCE_GROUP}"
        echo "  App URL:       ${url}"
        echo "  Health:        ${url}/health/live"
        echo "  WebSocket:     wss://${fqdn}/ws/twilio/{call_sid}"
        echo ""
        echo "  Next steps:"
        echo "    1. Configure Twilio phone number webhook:"
        echo "       POST → ${url}/twilio/inbound"
        echo "    2. Set Twilio Media Stream websocket URL:"
        echo "       wss://${fqdn}/ws/twilio/{streamSid}"
        echo "    3. Monitor logs:"
        echo "       az monitor log-analytics query --workspace <workspace-id> --analytics-query 'ContainerAppConsoleLogs_CL | take 50'"
        echo ""

    else
        log_info "AKS deployment applied. Check status with:"
        echo "  kubectl get pods -n construction-receptionist"
        echo "  kubectl get svc -n construction-receptionist"
    fi
}

# ---------------------------------------------------------------------------
# Phase 7: Output Configuration
# ---------------------------------------------------------------------------

print_outputs() {
    log_step "Phase 7: Deployment Outputs"

    echo ""
    echo "Resource Group: ${RESOURCE_GROUP}"
    echo ""

    if [[ "$TARGET" == "aca" ]]; then
        az deployment group show \
            --resource-group "${RESOURCE_GROUP}" \
            --name "main-construction" \
            --query "properties.outputs" \
            -o table 2>/dev/null || true
    fi

    echo ""
    echo "To redeploy after code changes:"
    echo "  ./scripts/deploy-construction.sh ${TARGET} ${ENVIRONMENT} ${LOCATION}"
    echo ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  Construction Receptionist — Azure Deployment${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  Target:       ${TARGET}"
    echo "  Environment:  ${ENVIRONMENT}"
    echo "  Location:     ${LOCATION}"
    echo "  Image:        ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"
    echo ""

    check_prerequisites
    build_image
    provision_infrastructure
    push_image
    configure_secrets
    deploy_application
    verify_deployment
    print_outputs

    log_info "All done."
}

main "$@"
