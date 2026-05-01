/**
 * Network Infrastructure Module
 * Creates VNet with subnets for AKS, Application Gateway, and private endpoints.
 * Ref: Microsoft (2024). AKS networking best practices. learn.microsoft.com/azure/aks/configure-kubenet
 */

@description('Azure region')
param location string = resourceGroup().location

@description('Environment name')
param environment string = 'prod'

@description('VNet address space')
param vnetAddressPrefix string = '10.0.0.0/16'

@description('AKS subnet address prefix')
param aksSubnetPrefix string = '10.0.0.0/20'

@description('Application Gateway subnet address prefix')
param appGatewaySubnetPrefix string = '10.0.16.0/24'

@description('Private endpoints subnet address prefix')
param privateEndpointsSubnetPrefix string = '10.0.17.0/24'

var vnetName = 'vnet-voice-${environment}'
var aksSubnetName = 'snet-aks'
var appGatewaySubnetName = 'snet-appgw'
var privateEndpointsSubnetName = 'snet-private'

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: aksSubnetName
        properties: {
          addressPrefix: aksSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
      {
        name: appGatewaySubnetName
        properties: {
          addressPrefix: appGatewaySubnetPrefix
        }
      }
      {
        name: privateEndpointsSubnetName
        properties: {
          addressPrefix: privateEndpointsSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

resource nsgAks 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: 'nsg-aks-${environment}'
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowHTTPS'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'AllowWebSocket'
        properties: {
          priority: 110
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '80'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output vnetName string = vnet.name
output aksSubnetId string = vnet.properties.subnets[0].id
output appGatewaySubnetId string = vnet.properties.subnets[1].id
output privateEndpointsSubnetId string = vnet.properties.subnets[2].id
