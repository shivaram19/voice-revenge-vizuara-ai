/**
 * Azure AI Search Module
 * Standard tier with semantic ranking for VoiceAgentRAG Slow Thinker.
 * Ref: Microsoft (2024). Azure AI Search. learn.microsoft.com/azure/search/
 */

@description('Azure region')
param location string = resourceGroup().location

@description('Environment name')
param environment string = 'prod'

var searchName = 'srch-voice-${environment}-${uniqueString(resourceGroup().id)}'

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchName
  location: location
  sku: {
    name: 'standard'
  }
  properties: {
    replicaCount: 2
    partitionCount: 1
    semanticSearch: 'standard'
    publicNetworkAccess: 'Enabled'
    networkRuleSet: {
      ipRules: []
      bypass: 'AzureServices'
    }
  }
}

output searchName string = search.name
output searchEndpoint string = 'https://${searchName}.search.windows.net'
output searchId string = search.id
