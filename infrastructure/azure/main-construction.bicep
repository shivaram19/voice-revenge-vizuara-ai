/**
 * Construction Receptionist — Simplified Azure Infrastructure
 * Ref: Microsoft (2024). Azure Well-Architected Framework [^44].
 *
 * Design: Azure Container Apps (not AKS) for 10-50 concurrent call scale.
 * No GPU. No self-hosted STT/TTS. Cloud APIs only (Azure OpenAI + Twilio).
 * SQLite backend eliminates database infrastructure complexity.
 */

@description('Azure region')
param location string = resourceGroup().location

@description('Environment: dev, staging, prod')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'prod'

@description('Container Apps CPU cores (0.5 to 2.0)')
param containerCpu string = '1.0'

@description('Container Apps memory (Gi)')
param containerMemory string = '2.0Gi'

@description('Minimum replicas')
param minReplicas int = 2

@description('Maximum replicas')
param maxReplicas int = 10

var commonTags = {
  project: 'construction-receptionist'
  environment: environment
  managedBy: 'bicep'
  costCenter: 'engineering'
}

var baseName = 'buildpro-${environment}'

// ---- Log Analytics (required by Container Apps) ----
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${baseName}-logs'
  location: location
  tags: commonTags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ---- Application Insights ----
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${baseName}-appinsights'
  location: location
  tags: commonTags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ---- Container Registry ----
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: '${baseName}acr'
  location: location
  tags: commonTags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: true
  }
}

// ---- Key Vault ----
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${baseName}-kv'
  location: location
  tags: commonTags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    accessPolicies: []
  }
}

// ---- Azure OpenAI ----
resource openAi 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: '${baseName}-openai'
  location: location
  tags: commonTags
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: '${baseName}-openai'
    publicNetworkAccess: 'Enabled'
  }
}

resource gptDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAi
  name: 'gpt-4o-mini'
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: '2024-07-18'
    }
  }
}

// ---- Azure Cache for Redis ----
resource redis 'Microsoft.Cache/redis@2024-03-01' = {
  name: '${baseName}-redis'
  location: location
  tags: commonTags
  properties: {
    sku: { name: 'Basic', family: 'C', capacity: 0 }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
  }
}

// ---- Container Apps Environment ----
resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${baseName}-env'
  location: location
  tags: commonTags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ---- Container App: Construction Receptionist ----
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${baseName}-app'
  location: location
  tags: commonTags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.name
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
        {
          name: 'azure-openai-key'
          value: openAi.listKeys().key1
        }
        {
          name: 'redis-key'
          value: redis.listKeys().primaryKey
        }
        {
          name: 'twilio-account-sid'
          value: ''
        }
        {
          name: 'twilio-auth-token'
          value: ''
        }
        {
          name: 'deepgram-api-key'
          value: ''
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'receptionist'
          image: '${acr.properties.loginServer}/construction-receptionist:latest'
          resources: {
            cpu: json(containerCpu)
            memory: containerMemory
          }
          env: [
            { name: 'APP_ENV', value: environment }
            { name: 'LOG_LEVEL', value: environment == 'prod' ? 'warn' : 'info' }
            { name: 'PORT', value: '8000' }
            { name: 'PYTHONUNBUFFERED', value: '1' }
            { name: 'COMPANY_NAME', value: 'BuildPro Contracting' }
            { name: 'BUSINESS_HOURS', value: 'Monday through Friday, 8 AM to 6 PM. Emergency dispatch 24/7.' }
            { name: 'AZURE_OPENAI_ENDPOINT', value: openAi.properties.endpoint }
            { name: 'AZURE_OPENAI_DEPLOYMENT', value: gptDeployment.name }
            { name: 'AZURE_OPENAI_API_VERSION', value: '2024-06-01' }
            {
              name: 'AZURE_OPENAI_KEY'
              secretRef: 'azure-openai-key'
            }
            {
              name: 'REDIS_HOST'
              value: redis.properties.hostName
            }
            {
              name: 'REDIS_PORT'
              value: '6380'
            }
            {
              name: 'REDIS_SSL'
              value: 'true'
            }
            {
              name: 'REDIS_KEY'
              secretRef: 'redis-key'
            }
            {
              name: 'TWILIO_ACCOUNT_SID'
              secretRef: 'twilio-account-sid'
            }
            {
              name: 'TWILIO_AUTH_TOKEN'
              secretRef: 'twilio-auth-token'
            }
            {
              name: 'DEEPGRAM_API_KEY'
              secretRef: 'deepgram-api-key'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsights.properties.ConnectionString
            }
          ]
          volumeMounts: [
            {
              volumeName: 'data'
              mountPath: '/app/data'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health/live'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 15
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health/ready'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              timeoutSeconds: 3
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-concurrency'
            custom: {
              type: 'http'
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
      volumes: [
        {
          name: 'data'
          storageType: 'EmptyDir'
        }
      ]
    }
  }
}

// ---- Role Assignment: Container App → Key Vault ----
resource keyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerApp.id, keyVault.id, 'secrets-user')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: containerApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ---- Outputs ----
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output acrPassword string = acr.listCredentials().passwords[0].value

output openAIEndpoint string = openAi.properties.endpoint
output openAIKey string = openAi.listKeys().key1

output redisHost string = redis.properties.hostName
output redisKey string = redis.listKeys().primaryKey

output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri

output appInsightsConnectionString string = appInsights.properties.ConnectionString

output containerAppName string = containerApp.name
output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
