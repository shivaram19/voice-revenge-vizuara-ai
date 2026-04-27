# Azure Setup Guide: AI Receptionist Deployment

**Version**: 1.0  
**Date**: 2026-04-25  
**Scope**: End-to-end Azure deployment for the Voice Agent Platform.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Azure CLI | >= 2.60 | Resource provisioning |
| kubectl | >= 1.29 | Kubernetes operations |
| Kustomize | >= 5.0 | Manifest templating |
| Docker | >= 24.0 | Container builds |
| Python | >= 3.11 | Local testing |

---

## Step 1: Azure Subscription Preparation

### 1.1 Request GPU Quota

GPU VMs require quota increases. Submit requests **2-3 days before deployment**.

```bash
# List current quota
az vm list-usage --location eastus --output table | grep -i "NC\|ND"

# Request quota increase via Azure Portal:
# Subscriptions → <your-sub> → Usage + quotas → Request increase
# Request: NCv3 Family = 24 cores minimum
```

**Required quota** (per region):
- NCv3 Family: 24 cores (STT node pool)
- NC A100 v4 Family: 48 cores (LLM node pool)

### 1.2 Register Resource Providers

```bash
az provider register --namespace Microsoft.ContainerService
az provider register --namespace Microsoft.Compute
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.Cache
az provider register --namespace Microsoft.Search
```

---

## Step 2: Deploy Infrastructure (Bicep)

### 2.1 Authenticate

```bash
az login
az account set --subscription "<your-subscription-id>"
```

### 2.2 Deploy All Resources

```bash
# Production
./scripts/deploy-infra.sh prod eastus

# Development
./scripts/deploy-infra.sh dev eastus
```

This creates:
- Resource Group
- VNet with subnets
- AKS cluster with GPU node pools
- Azure Container Registry
- Azure OpenAI Service
- Azure Cache for Redis
- Azure AI Search
- Azure Blob Storage
- Azure Key Vault
- Log Analytics + Application Insights

### 2.3 Capture Outputs

```bash
# Get deployment outputs
az deployment group show \
  --resource-group rg-voice-prod \
  --name mainDeploy \
  --query properties.outputs
```

Save these values — they are needed for K8s secrets.

---

## Step 3: Configure Secrets

### 3.1 Twilio Credentials

```bash
KV_NAME=$(az keyvault list --resource-group rg-voice-prod --query "[0].name" -o tsv)

az keyvault secret set --vault-name $KV_NAME \
  --name twilio-auth-token --value "<your-twilio-auth-token>"

az keyvault secret set --vault-name $KV_NAME \
  --name twilio-account-sid --value "<your-twilio-account-sid>"
```

### 3.2 Azure OpenAI Key

```bash
OPENAI_NAME=$(az cognitiveservices account list --resource-group rg-voice-prod \
  --query "[?kind=='OpenAI'].name | [0]" -o tsv)

OPENAI_KEY=$(az cognitiveservices account keys list \
  --name $OPENAI_NAME --resource-group rg-voice-prod --query key1 -o tsv)

az keyvault secret set --vault-name $KV_NAME \
  --name azure-openai-key --value "$OPENAI_KEY"
```

### 3.3 Redis Key

```bash
REDIS_NAME=$(az redisenterprise list --resource-group rg-voice-prod \
  --query "[0].name" -o tsv)

REDIS_KEY=$(az redisenterprise database list-keys \
  --cluster-name $REDIS_NAME --resource-group rg-voice-prod \
  --database-name default --query primaryKey -o tsv)

az keyvault secret set --vault-name $KV_NAME \
  --name redis-primary-key --value "$REDIS_KEY"
```

### 3.4 Remaining Secrets

```bash
# Azure AI Search
SEARCH_NAME=$(az search service list --resource-group rg-voice-prod \
  --query "[0].name" -o tsv)
SEARCH_KEY=$(az search admin-key show --service-name $SEARCH_NAME \
  --resource-group rg-voice-prod --query primaryKey -o tsv)
az keyvault secret set --vault-name $KV_NAME --name search-key --value "$SEARCH_KEY"

# Blob Storage
STORAGE_NAME=$(az storage account list --resource-group rg-voice-prod \
  --query "[?contains(name,'stvoice')].name | [0]" -o tsv)
STORAGE_CONN=$(az storage account show-connection-string \
  --name $STORAGE_NAME --resource-group rg-voice-prod --query connectionString -o tsv)
az keyvault secret set --vault-name $KV_NAME \
  --name storage-connection-string --value "$STORAGE_CONN"

# Application Insights
APPINSIGHTS_CONN=$(az monitor app-insights component show \
  --app appi-voice-prod --resource-group rg-voice-prod \
  --query connectionString -o tsv)
az keyvault secret set --vault-name $KV_NAME \
  --name appinsights-connection-string --value "$APPINSIGHTS_CONN"
```

---

## Step 4: Configure AKS

### 4.1 Get Credentials

```bash
az aks get-credentials \
  --resource-group rg-voice-prod \
  --name aks-voice-prod \
  --overwrite-existing
```

### 4.2 Install NGINX Ingress Controller

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz
```

### 4.3 Install cert-manager

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

### 4.4 Install External Secrets Operator

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace
```

### 4.5 Configure Workload Identity

```bash
# Enable workload identity on AKS
az aks update \
  --resource-group rg-voice-prod \
  --name aks-voice-prod \
  --enable-oidc-issuer \
  --enable-workload-identity

# Create federated identity credential (one-time setup)
# See: https://learn.microsoft.com/azure/aks/workload-identity-deploy-cluster
```

---

## Step 5: Build and Push Containers

### 5.1 Log in to ACR

```bash
ACR_NAME=$(az acr list --resource-group rg-voice-prod --query "[0].name" -o tsv)
az acr login --name $ACR_NAME
```

### 5.2 Build Images

```bash
# Agent Controller
docker build -f docker/Dockerfile.agent -t ${ACR_NAME}.azurecr.io/agent-controller:prod .
docker push ${ACR_NAME}.azurecr.io/agent-controller:prod

# STT Service (requires Docker BuildKit for multi-stage)
export DOCKER_BUILDKIT=1
docker build -f docker/Dockerfile.stt -t ${ACR_NAME}.azurecr.io/stt-service:prod .
docker push ${ACR_NAME}.azurecr.io/stt-service:prod

# TTS Service
docker build -f docker/Dockerfile.tts -t ${ACR_NAME}.azurecr.io/tts-service:prod .
docker push ${ACR_NAME}.azurecr.io/tts-service:prod
```

---

## Step 6: Deploy to Kubernetes

### 6.1 Create Secrets Manually (or use External Secrets Operator)

```bash
kubectl create namespace voice-agent --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic voice-agent-secrets \
  --namespace voice-agent \
  --from-literal=azure-openai-endpoint="https://$OPENAI_NAME.openai.azure.com" \
  --from-literal=azure-openai-key="$OPENAI_KEY" \
  --from-literal=redis-host="$REDIS_NAME.$LOCATION.redisenterprise.cache.azure.net" \
  --from-literal=redis-key="$REDIS_KEY" \
  --from-literal=search-endpoint="https://$SEARCH_NAME.search.windows.net" \
  --from-literal=search-key="$SEARCH_KEY" \
  --from-literal=storage-connection-string="$STORAGE_CONN" \
  --from-literal=twilio-account-sid="<your-sid>" \
  --from-literal=twilio-auth-token="<your-token>" \
  --from-literal=appinsights-connection-string="$APPINSIGHTS_CONN"
```

### 6.2 Apply Manifests

```bash
# Production
./scripts/deploy-k8s.sh prod

# Development
./scripts/deploy-k8s.sh dev
```

### 6.3 Verify Deployment

```bash
kubectl get pods -n voice-agent
kubectl get svc -n voice-agent
kubectl get ingress -n voice-agent
kubectl logs -n voice-agent -l app=agent-controller --tail=50
```

---

## Step 7: Configure Twilio

### 7.1 Create a TwiML App

In the Twilio Console:
1. **Phone Numbers → Manage → Active Numbers**
2. Select your number → **Configure**
3. Under **Voice & Fax**:
   - **A call comes in**: Webhook → `https://voice.acme-medical.com/twilio/voice`
   - **Primary handler fails**: Webhook → `https://voice.acme-medical.com/twilio/fallback`

### 7.2 Configure Media Streams

Your `/twilio/voice` endpoint must return TwiML that starts a Media Stream:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://voice.acme-medical.com/ws/twilio" />
  </Connect>
</Response>
```

---

## Step 8: Observability Setup

### 8.1 Access Grafana

```bash
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# Open http://localhost:3000 (default creds: admin/prom-operator)
```

### 8.2 Import Dashboards

Dashboard JSON files (if created) can be imported via Grafana UI:
- **Voice Agent Overview**: Turn-gap P95, active sessions, error rate
- **STT Performance**: WER, latency, GPU utilization
- **LLM Performance**: TTFT, token throughput, queue depth
- **TTS Performance**: TTFB, RTF, synthesis count

### 8.3 Configure Azure Alerts

```bash
# Turn-gap latency alert
az monitor metrics alert create \
  --name "HighTurnGapLatency" \
  --resource-group rg-voice-prod \
  --scopes $(az aks show --name aks-voice-prod --resource-group rg-voice-prod --query id -o tsv) \
  --condition "avg voice_agent_turn_gap_seconds > 0.5" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --severity 2 \
  --action $(az monitor action-group list --resource-group rg-voice-prod --query "[0].id" -o tsv)
```

---

## Step 9: Post-Deployment Validation

### 9.1 End-to-End Test Call

```bash
# Use Twilio's Test Credentials for a simulated call
curl -X POST https://api.twilio.com/2010-04-01/Accounts/<sid>/Calls.json \
  --data-urlencode "Url=https://voice.acme-medical.com/twilio/voice" \
  --data-urlencode "To=+15555555555" \
  --data-urlencode "From=+15555555556" \
  -u <sid>:<auth_token>
```

### 9.2 Check Metrics

```bash
# Active sessions
kubectl exec -n voice-agent deploy/prod-agent-controller -- \
  curl -s localhost:9090/metrics | grep voice_agent_active_sessions

# Turn-gap latency
kubectl exec -n voice-agent deploy/prod-agent-controller -- \
  curl -s localhost:9090/metrics | grep voice_agent_turn_gap_seconds
```

---

## Troubleshooting

See [troubleshooting.md](troubleshooting.md) for common issues.

---

## References
[^43]: Twilio. (2024). Media Streams API. twilio.com/docs/voice/media-streams.
[^43]: Twilio. (2024). Media Streams API. twilio.com/docs/voice/media-streams.
[^44]: Microsoft. (2024). Azure OpenAI Service. learn.microsoft.com/azure/ai-services/openai/.
[^44]: Microsoft. (2024). Deploy an Azure Kubernetes Service cluster. learn.microsoft.com/azure/aks/learn/quick-kubernetes-deploy-portal.
[^44]: Microsoft. (2024). Use GPUs for compute-intensive workloads on AKS. learn.microsoft.com/azure/aks/gpu-cluster.
[^44]: Microsoft. (2024). Azure OpenAI Service. learn.microsoft.com/azure/ai-services/openai/.

[^1]: Microsoft. (2024). Deploy an Azure Kubernetes Service cluster. learn.microsoft.com/azure/aks/learn/quick-kubernetes-deploy-portal.
[^2]: Microsoft. (2024). Use GPUs for compute-intensive workloads on AKS. learn.microsoft.com/azure/aks/gpu-cluster.
[^3]: Twilio. (2024). Media Streams API. twilio.com/docs/voice/media-streams.
[^4]: Microsoft. (2024). Azure OpenAI Service. learn.microsoft.com/azure/ai-services/openai/.
