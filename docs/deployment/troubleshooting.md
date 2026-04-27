# Azure Deployment Troubleshooting

**Version**: 1.0  
**Date**: 2026-04-25

---

## Infrastructure (Bicep)

### `InvalidTemplateDeployment` — GPU quota exceeded

**Symptom**: Deployment fails with `Operation could not be completed as it results in exceeding approved standardNCADSA100v4Family Cores quota`.

**Fix**:
1. Check current quota: `az vm list-usage --location eastus --output table | grep NC`
2. Request increase: Azure Portal → Subscriptions → Usage + quotas → Request increase
3. Alternative: Use `Standard_NC6s_v3` (older V100) in `aks.bicep` parameters.

### `Conflict` — Resource group already exists in different region

**Symptom**: `Resource group 'rg-voice-prod' already exists in location 'westus'`.

**Fix**: Delete existing RG or use a different name: `./scripts/deploy-infra.sh prod westus2`.

---

## Kubernetes

### Pods stuck in `Pending` — GPU nodes not available

**Symptom**: `kubectl get pods` shows STT pods in Pending with `Insufficient nvidia.com/gpu`.

**Fix**:
```bash
# Check if GPU node pool is scaling
kubectl get nodes -l workload=gpu-stt

# If no nodes, check cluster-autoscaler logs
kubectl logs -n kube-system deployment/cluster-autoscaler

# Manual fix: scale node pool
az aks nodepool scale \
  --resource-group rg-voice-prod \
  --cluster-name aks-voice-prod \
  --name gpustt \
  --node-count 2
```

### `ImagePullBackOff` — ACR authentication

**Symptom**: Pods fail to start with `Failed to pull image`.

**Fix**:
```bash
# Verify ACR pull role binding
az role assignment list \
  --scope $(az acr show --name <acr-name> --query id -o tsv) \
  --query "[?roleDefinitionName=='AcrPull']"

# Re-create role assignment if missing
az aks update \
  --resource-group rg-voice-prod \
  --name aks-voice-prod \
  --attach-acr <acr-name>
```

### `CrashLoopBackOff` — Missing secrets

**Symptom**: Agent controller restarts repeatedly.

**Fix**:
```bash
# Check logs
kubectl logs -n voice-agent deployment/prod-agent-controller --previous

# Verify secrets exist
kubectl get secret voice-agent-secrets -n voice-agent

# Re-create if needed
kubectl create secret generic voice-agent-secrets ...
```

---

## Twilio WebSocket

### `Connection refused` — Ingress not configured

**Symptom**: Twilio Event Streams shows `Connection refused` or `TLS handshake failed`.

**Fix**:
```bash
# Check ingress status
kubectl get ingress -n voice-agent

# Verify DNS resolves
dig voice.acme-medical.com

# Check cert-manager
kubectl get certificates -n voice-agent
kubectl describe certificate voice-agent-tls -n voice-agent

# If cert is stuck, check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```

### No audio received — STT service down

**Symptom**: Call connects but agent never responds.

**Fix**:
```bash
# Check STT pod status
kubectl get pods -n voice-agent -l app=stt-service

# Check STT logs
kubectl logs -n voice-agent -l app=stt-service --tail=100

# Verify GPU is available inside pod
kubectl exec -n voice-agent -it deploy/prod-stt-service -- nvidia-smi
```

---

## Performance

### Turn-gap latency > 500ms

**Symptom**: P95 turn-gap exceeds SLO.

**Diagnosis**:
```bash
# Check per-service latency
kubectl exec -n voice-agent deploy/prod-agent-controller -- \
  curl -s localhost:9090/metrics | grep voice_agent_turn_gap_seconds_bucket

# Check GPU utilization
kubectl top nodes -l workload=gpu-stt

# Check LLM queue depth (if using vLLM)
kubectl exec -n voice-agent deploy/prod-stt-service -- \
  curl -s localhost:8000/metrics | grep vllm_queue
```

**Fix**:
1. Scale STT pods: `kubectl scale deployment prod-stt-service --replicas=6 -n voice-agent`
2. Enable vLLM fallback if Azure OpenAI is throttling.
3. Check Redis cache hit rate — if <75%, increase cache size.

---

## Cost

### Unexpected GPU charges

**Symptom**: Monthly bill significantly higher than estimate.

**Diagnosis**:
```bash
# Check actual node count
kubectl get nodes

# Check if GPU nodes are scaling down
kubectl logs -n kube-system deployment/cluster-autoscaler | grep "scale-down"
```

**Fix**:
1. Reduce `gpu-stt` minCount to 1 in `aks.bicep` for dev/staging.
2. Use spot instances for non-critical workloads.
3. Schedule scale-down: `kubectl create cronjob gpu-scale-down --schedule="0 20 * * *" --image=bitnami/kubectl -- kubectl scale deployment prod-stt-service --replicas=1 -n voice-agent`.

---

## References
[^43]: Twilio. (2024). Media Streams troubleshooting. twilio.com/docs/voice/media-streams/troubleshooting.
[^44]: Microsoft. (2024). AKS troubleshooting. learn.microsoft.com/azure/aks/troubleshooting.
[^58]: NVIDIA. (2024). GPU Operator troubleshooting. docs.nvidia.com/datacenter/cloud-native/gpu-operator/troubleshooting.html.

[^1]: Microsoft. (2024). AKS troubleshooting. learn.microsoft.com/azure/aks/troubleshooting.
[^2]: Twilio. (2024). Media Streams troubleshooting. twilio.com/docs/voice/media-streams/troubleshooting.
[^3]: NVIDIA. (2024). GPU Operator troubleshooting. docs.nvidia.com/datacenter/cloud-native/gpu-operator/troubleshooting.html.
