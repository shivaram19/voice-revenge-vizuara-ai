/**
 * Azure Kubernetes Service Module
 * AKS cluster with GPU node pools for STT (Distil-Whisper) and LLM (vLLM fallback).
 * Ref: Microsoft (2024). AKS GPU node pools. learn.microsoft.com/azure/aks/gpu-cluster/
 * Ref: NVIDIA (2023). MIG User Guide. docs.nvidia.com/datacenter/tesla/mig-user-guide/
 */

@description('Azure region')
param location string = resourceGroup().location

@description('Environment name')
param environment string = 'prod'

@description('VNet subnet ID for AKS nodes')
param subnetId string

@description('ACR resource ID for pull access')
param acrId string

@description('Log Analytics workspace ID for monitoring')
param logAnalyticsWorkspaceId string

@description('Kubernetes version')
param kubernetesVersion string = '1.29'

@description('System node pool VM size')
param systemNodeVmSize string = 'Standard_D4s_v5'

@description('CPU workload node pool VM size')
param cpuNodeVmSize string = 'Standard_F48s_v2'

@description('GPU STT node pool VM size')
param gpuSttVmSize string = 'Standard_NC24ads_A100_v4'

@description('GPU LLM node pool VM size')
param gpuLlmVmSize string = 'Standard_NC48ads_A100_v4'

var clusterName = 'aks-voice-${environment}'
var dnsPrefix = 'voice-${environment}'

// Managed identity for AKS control plane
resource aksIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-07-31-preview' = {
  name: 'id-${clusterName}'
  location: location
}

// AKS cluster with system node pool only (GPU pools added separately)
resource aks 'Microsoft.ContainerService/managedClusters@2024-02-01' = {
  name: clusterName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${aksIdentity.id}': {}
    }
  }
  properties: {
    kubernetesVersion: kubernetesVersion
    dnsPrefix: dnsPrefix
    enableRBAC: true
    networkProfile: {
      networkPlugin: 'azure'
      networkPolicy: 'calico'
      serviceCidr: '10.1.0.0/16'
      dnsServiceIP: '10.1.0.10'
    }
    addonProfiles: {
      azureKeyvaultSecretsProvider: {
        enabled: true
        config: {
          enableSecretRotation: 'true'
        }
      }
      omsAgent: {
        enabled: true
        config: {
          logAnalyticsWorkspaceResourceID: logAnalyticsWorkspaceId
        }
      }
    }
    agentPoolProfiles: [
      {
        name: 'system'
        count: 3
        vmSize: systemNodeVmSize
        osType: 'Linux'
        mode: 'System'
        vnetSubnetID: subnetId
        maxPods: 30
        type: 'VirtualMachineScaleSets'
        osDiskType: 'Managed'
        osDiskSizeGB: 128
      }
    ]
  }
}

// CPU workload node pool (Agent Controller, TTS, tools)
resource cpuNodePool 'Microsoft.ContainerService/managedClusters/agentPools@2024-02-01' = {
  parent: aks
  name: 'cpuworkloads'
  properties: {
    count: 3
    vmSize: cpuNodeVmSize
    osType: 'Linux'
    mode: 'User'
    vnetSubnetID: subnetId
    maxPods: 50
    minCount: 3
    maxCount: 50
    enableAutoScaling: true
    type: 'VirtualMachineScaleSets'
    osDiskType: 'Managed'
    osDiskSizeGB: 128
    nodeTaints: []
    nodeLabels: {
      workload: 'cpu'
    }
  }
}

// GPU STT node pool (Distil-Whisper ASR)
resource gpuSttNodePool 'Microsoft.ContainerService/managedClusters/agentPools@2024-02-01' = {
  parent: aks
  name: 'gpustt'
  properties: {
    count: 2
    vmSize: gpuSttVmSize
    osType: 'Linux'
    mode: 'User'
    vnetSubnetID: subnetId
    maxPods: 20
    minCount: 2
    maxCount: 20
    enableAutoScaling: true
    type: 'VirtualMachineScaleSets'
    osDiskType: 'Managed'
    osDiskSizeGB: 256
    nodeTaints: [
      'nvidia.com/gpu=true:NoSchedule'
    ]
    nodeLabels: {
      workload: 'gpu-stt'
      'nvidia.com/gpu.present': 'true'
    }
  }
}

// GPU LLM node pool (vLLM fallback)
resource gpuLlmNodePool 'Microsoft.ContainerService/managedClusters/agentPools@2024-02-01' = {
  parent: aks
  name: 'gpullm'
  properties: {
    count: 2
    vmSize: gpuLlmVmSize
    osType: 'Linux'
    mode: 'User'
    vnetSubnetID: subnetId
    maxPods: 20
    minCount: 2
    maxCount: 15
    enableAutoScaling: true
    type: 'VirtualMachineScaleSets'
    osDiskType: 'Managed'
    osDiskSizeGB: 256
    nodeTaints: [
      'nvidia.com/gpu=true:NoSchedule'
    ]
    nodeLabels: {
      workload: 'gpu-llm'
      'nvidia.com/gpu.present': 'true'
    }
  }
}

// Role assignment: AKS can pull from ACR
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, aks.id, acrId, 'AcrPull')
  scope: resourceId(split(acrId, '/')[2], split(acrId, '/')[4], 'Microsoft.ContainerRegistry/registries', last(split(acrId, '/')))
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: aks.properties.identityProfile.kubeletidentity.objectId
    principalType: 'ServicePrincipal'
  }
}

output aksName string = aks.name
output aksId string = aks.id
output aksFqdn string = aks.properties.fqdn
output aksIdentityClientId string = aksIdentity.properties.clientId
output aksIdentityPrincipalId string = aksIdentity.properties.principalId
