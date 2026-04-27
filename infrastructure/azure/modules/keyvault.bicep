/**
 * Azure Key Vault Module
 * Standard tier with private endpoint, RBAC, and secret placeholders.
 * Ref: Microsoft (2024). Key Vault best practices. learn.microsoft.com/azure/key-keys/
 */

@description('Azure region')
param location string = resourceGroup().location

@description('Environment name')
param environment string = 'prod'

@description('VNet subnet ID for private endpoint')
param subnetId string

@description('Tenant ID for RBAC')
param tenantId string = subscription().tenantId

var kvName = 'kv-voice-${environment}-${uniqueString(resourceGroup().id)}'

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  properties: {
    tenantId: tenantId
    sku: {
      name: 'standard'
      family: 'A'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}

resource kvPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: 'pe-${kvName}'
  location: location
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'pl-${kvName}'
        properties: {
          privateLinkServiceId: kv.id
          groupIds: [
            'vault'
          ]
        }
      }
    ]
  }
}

resource kvPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.vaultcore.azure.net'
  location: 'global'
}

// Placeholder secrets — populated post-deployment via scripts or pipeline
resource secretTwilioAuthToken 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'twilio-auth-token'
  properties: {
    value: 'PLACEHOLDER-UPDATE-AFTER-DEPLOY'
  }
}

resource secretTwilioAccountSid 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'twilio-account-sid'
  properties: {
    value: 'PLACEHOLDER-UPDATE-AFTER-DEPLOY'
  }
}

resource secretOpenAIKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'azure-openai-key'
  properties: {
    value: 'PLACEHOLDER-UPDATE-AFTER-DEPLOY'
  }
}

resource secretRedisKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'redis-primary-key'
  properties: {
    value: 'PLACEHOLDER-UPDATE-AFTER-DEPLOY'
  }
}

output keyVaultName string = kv.name
output keyVaultId string = kv.id
output keyVaultUri string = kv.properties.vaultUri
