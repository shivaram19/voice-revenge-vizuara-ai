# Azure Deployment — Construction Receptionist

Standalone deployment guide for the construction-specialized AI receptionist on Azure.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Azure Container Apps                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Construction Receptionist (FastAPI + WebSocket)        │   │
│  │  • SQLite backend (EmptyDir volume)                     │   │
│  │  • Contractor scheduling engine                         │   │
│  │  • Outbound call queue                                  │   │
│  │  • Emergency triage (3 levels)                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│  │ Azure OpenAI │  │ Azure Redis │  │ Azure Key Vault     │    │
│  │ (gpt-4o-mini)│  │ (sessions)  │  │ (Twilio secrets)    │    │
│  └─────────────┘  └─────────────┘  └─────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
         │
    Twilio PSTN
         │
   Caller Phone
```

**Scale target:** 10-50 concurrent calls  
**Compute:** No GPU required  
**STT/TTS:** Cloud APIs (Azure OpenAI + Twilio)  
**Backend:** SQLite (file-based, no managed DB)  

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| Azure CLI | Provision Azure resources | [aka.ms/installazurecli](https://aka.ms/installazurecli) |
| Docker | Build container image | [docker.com/get-docker](https://docker.com/get-docker) |
| Twilio account | PSTN telephony | [twilio.com](https://twilio.com) |

## Quick Start

```bash
# 1. Login to Azure
az login

# 2. Set environment variables for Twilio
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token"

# 3. Deploy (Azure Container Apps — recommended)
./scripts/deploy-construction.sh aca prod eastus

# 4. Or deploy to AKS (if you already have a cluster)
./scripts/deploy-construction.sh aks prod eastus
```

## Deployment Targets

### Azure Container Apps (ACA) — Recommended

Best for 10-50 concurrent calls. Serverless containers with auto-scaling.

**Provisioned resources:**
- Azure Container Apps Environment + App
- Azure Container Registry (Basic)
- Azure OpenAI Service (gpt-4o-mini, 10 TPM)
- Azure Cache for Redis (Basic C0)
- Azure Key Vault (Standard)
- Application Insights + Log Analytics

**Cost estimate (monthly, East US):**
| Resource | Tier | Est. Cost |
|----------|------|-----------|
| Container Apps | 2-10 replicas, 1 vCPU, 2 GiB | $50-150 |
| Azure OpenAI | gpt-4o-mini, 10K calls/day | $30-80 |
| Redis Cache | Basic C0 | $17 |
| Container Registry | Basic | $5 |
| Key Vault | Standard | ~$1 |
| App Insights | Pay-as-you-go | $5-15 |
| **Total** | | **~$110-270/month** |

### Azure Kubernetes Service (AKS)

Use if you already run AKS or need advanced networking.

**Provisioned resources:**
- AKS cluster (same as `main.bicep`)
- All supporting services (ACR, OpenAI, Redis, Key Vault)

## What the Script Does

The `deploy-construction.sh` script runs 7 phases:

```
Phase 0: Check prerequisites (az, docker, kubectl)
Phase 1: Build container image (linux/amd64)
Phase 2: Provision Azure infrastructure (Bicep)
Phase 3: Push image to Azure Container Registry
Phase 4: Configure Twilio secrets in Key Vault / Container App
Phase 5: Deploy application (ACA update or Kustomize)
Phase 6: Verify deployment (health check)
Phase 7: Print outputs and next steps
```

## Post-Deployment: Configure Twilio

After deployment, configure your Twilio phone number:

1. **Voice webhook URL:**
   ```
   POST https://<your-app-fqdn>/twilio/inbound
   ```

2. **Media Stream websocket URL:**
   ```
   wss://<your-app-fqdn>/ws/twilio/{streamSid}
   ```

Find your app FQDN:
```bash
az containerapp show \
  --name buildpro-prod-app \
  --resource-group rg-buildpro-prod \
  --query "properties.configuration.ingress.fqdn" \
  -o tsv
```

## Monitoring

View container logs:
```bash
az containerapp logs show \
  --name buildpro-prod-app \
  --resource-group rg-buildpro-prod \
  --follow
```

Query Application Insights:
```bash
az monitor log-analytics query \
  --workspace $(az deployment group show \
    --resource-group rg-buildpro-prod \
    --name main-construction \
    --query "properties.outputs.logAnalyticsWorkspaceName.value" \
    -o tsv) \
  --analytics-query "ContainerAppConsoleLogs_CL | take 50"
```

## Rolling Back

```bash
# Revert to previous image
az containerapp update \
  --name buildpro-prod-app \
  --resource-group rg-buildpro-prod \
  --image buildproprodacr.azurecr.io/construction-receptionist:prod
```

## Files

| File | Purpose |
|------|---------|
| `scripts/deploy-construction.sh` | Main deployment script |
| `infrastructure/azure/main-construction.bicep` | Simplified Bicep for construction |
| `infrastructure/azure/parameters.construction.json` | Bicep parameters |
| `docker/Dockerfile.construction` | Construction-specific Dockerfile |
| `k8s/construction/base/` | Base K8s manifests (namespace, deployment, service, HPA) |
| `k8s/construction/overlays/prod/` | Production Kustomize overlay |

## References

- [^44]: Microsoft. (2024). Azure Well-Architected Framework.
- [^41]: Twilio. (2024). REST API: Making Calls.
- [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch.
