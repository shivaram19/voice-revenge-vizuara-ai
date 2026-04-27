/**
 * Azure Cache for Redis Module
 * Enterprise tier with clustering for session state and semantic cache.
 * Ref: Microsoft (2024). Azure Cache for Redis. learn.microsoft.com/azure/azure-cache-for-redis/
 */

@description('Azure region')
param location string = resourceGroup().location

@description('Environment name')
param environment string = 'prod'

@description('Redis SKU name')
param skuName string = 'Enterprise_E10'

var redisName = 'redis-voice-${environment}-${uniqueString(resourceGroup().id)}'

resource redis 'Microsoft.Cache/redisEnterprise@2024-02-01' = {
  name: redisName
  location: location
  sku: {
    name: skuName
  }
  properties: {
    minimumTlsVersion: '1.2'
  }
}

resource redisDb 'Microsoft.Cache/redisEnterprise/databases@2024-02-01' = {
  parent: redis
  name: 'default'
  properties: {
    clientProtocol: 'Encrypted'
    port: 10000
    clusteringPolicy: 'EnterpriseCluster'
    evictionPolicy: 'AllKeysLRU'
    modules: [
      {
        name: 'RediSearch'
      }
      {
        name: 'RedisJSON'
      }
    ]
  }
}

output redisHost string = redis.properties.hostName
output redisName string = redis.name
output redisId string = redis.id
