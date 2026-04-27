/**
 * Root Bicep Module — Azure Voice Agent Platform Infrastructure
 * Orchestrates all modules for end-to-end deployment.
 * Ref: ADR-005; Microsoft (2024). Azure Well-Architected Framework.
 */

@description('Azure region')
param location string = resourceGroup().location

@description('Environment name: dev, staging, prod')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'prod'

@description('Kubernetes version')
param kubernetesVersion string = '1.29'

// Tags applied to all resources
var commonTags = {
  project: 'voice-agent-platform'
  environment: environment
  managedBy: 'bicep'
  costCenter: 'engineering'
}

// ---- Network ----
module network 'modules/network.bicep' = {
  name: 'networkDeploy'
  params: {
    location: location
    environment: environment
  }
}

// ---- Monitoring (needed by AKS addon) ----
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoringDeploy'
  params: {
    location: location
    environment: environment
  }
}

// ---- Container Registry ----
module acr 'modules/acr.bicep' = {
  name: 'acrDeploy'
  params: {
    location: location
    environment: environment
    subnetId: network.outputs.privateEndpointsSubnetId
  }
}

// ---- Key Vault ----
module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvaultDeploy'
  params: {
    location: location
    environment: environment
    subnetId: network.outputs.privateEndpointsSubnetId
  }
}

// ---- Azure OpenAI ----
module openai 'modules/openai.bicep' = {
  name: 'openaiDeploy'
  params: {
    location: location
    environment: environment
  }
}

// ---- Redis Cache ----
module redis 'modules/redis.bicep' = {
  name: 'redisDeploy'
  params: {
    location: location
    environment: environment
  }
}

// ---- Azure AI Search ----
module search 'modules/search.bicep' = {
  name: 'searchDeploy'
  params: {
    location: location
    environment: environment
  }
}

// ---- Blob Storage ----
module storage 'modules/storage.bicep' = {
  name: 'storageDeploy'
  params: {
    location: location
    environment: environment
    subnetId: network.outputs.privateEndpointsSubnetId
  }
}

// ---- AKS Cluster (depends on monitoring for omsAgent addon) ----
module aks 'modules/aks.bicep' = {
  name: 'aksDeploy'
  params: {
    location: location
    environment: environment
    subnetId: network.outputs.aksSubnetId
    acrId: acr.outputs.acrId
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    kubernetesVersion: kubernetesVersion
  }
}

// ---- Outputs ----
output environment string = environment
output location string = location

output vnetName string = network.outputs.vnetName
output vnetId string = network.outputs.vnetId

output acrName string = acr.outputs.acrName
output acrLoginServer string = acr.outputs.acrLoginServer

output keyVaultName string = keyvault.outputs.keyVaultName
output keyVaultUri string = keyvault.outputs.keyVaultUri

output openAIEndpoint string = openai.outputs.openAIEndpoint
output openAIName string = openai.outputs.openAIName
output gptDeploymentName string = openai.outputs.gptDeploymentName

output redisHost string = redis.outputs.redisHost
output redisName string = redis.outputs.redisName

output searchName string = search.outputs.searchName
output searchEndpoint string = search.outputs.searchEndpoint

output storageName string = storage.outputs.storageName
output storageEndpoint string = storage.outputs.storageEndpoint

output aksName string = aks.outputs.aksName
output aksFqdn string = aks.outputs.aksFqdn

output logAnalyticsWorkspaceName string = monitoring.outputs.logAnalyticsWorkspaceName
output appInsightsName string = monitoring.outputs.appInsightsName
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString
