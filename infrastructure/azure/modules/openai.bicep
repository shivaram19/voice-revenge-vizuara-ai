/**
 * Azure OpenAI Service Module
 * Creates OpenAI account with GPT-4o-mini deployment for receptionist LLM.
 * Ref: Microsoft (2024). Azure OpenAI Service. learn.microsoft.com/azure/ai-services/openai/
 */

@description('Azure region')
param location string = resourceGroup().location

@description('Environment name')
param environment string = 'prod'

@description('GPT model deployment name')
param gptDeploymentName string = 'gpt-4o-mini'

@description('GPT model name')
param gptModelName string = 'gpt-4o-mini'

@description('GPT model version')
param gptModelVersion string = '2024-07-18'

@description('Tokens per minute capacity')
param tokensPerMinute int = 100000

var openAIName = 'aoai-voice-${environment}-${uniqueString(resourceGroup().id)}'

resource openAI 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: openAIName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openAIName
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      ipRules: []
    }
  }
}

resource gptDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openAI
  name: gptDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 100
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: gptModelName
      version: gptModelVersion
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
}

output openAIEndpoint string = openAI.properties.endpoint
output openAIName string = openAI.name
output openAIId string = openAI.id
output gptDeploymentName string = gptDeployment.name
