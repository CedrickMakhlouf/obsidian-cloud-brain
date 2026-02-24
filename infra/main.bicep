// ============================================================
// Obsidian Cloud Brain – Infrastructure as Code (Azure Bicep)
// Sets up the full Azure environment with a single command:
//   az deployment group create \
//     --resource-group rg-obsidian-brain \
//     --template-file infra/main.bicep \
//     --parameters @infra/params.json
// ============================================================

@description('Location for all resources (default: resource group location)')
param location string = resourceGroup().location

@description('Prefix for all resource names')
param prefix string = 'obsidian'

@description('SKU for Azure AI Search')
@allowed(['free', 'basic', 'standard'])
param searchSku string = 'basic'

// ── Variables ─────────────────────────────────────────────────────────────────
var storageAccountName = '${prefix}storage${uniqueString(resourceGroup().id)}'
var searchServiceName = '${prefix}-search'
var containerAppEnvName = '${prefix}-env'
var containerAppName = '${prefix}-api'
var logAnalyticsName = '${prefix}-logs'

// ── Azure Storage Account ─────────────────────────────────────────────────────
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource vaultContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'obsidian-vault'
  properties: { publicAccess: 'None' }
}

// ── Azure AI Search ───────────────────────────────────────────────────────────
resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: searchServiceName
  location: location
  sku: { name: searchSku }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
  }
}

// ── Log Analytics Workspace (for Container Apps monitoring) ────────────────────
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ── Azure Container Apps Environment ─────────────────────────────────────────
resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppEnvName
  location: location
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

// ── Azure Container App (FastAPI) ─────────────────────────────────────────────
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
      }
    }
    template: {
      containers: [
        {
          name: 'obsidian-api'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // Replace with your own image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'AZURE_SEARCH_SERVICE_ENDPOINT', value: 'https://${searchServiceName}.search.windows.net' }
            { name: 'AZURE_STORAGE_CONTAINER_NAME', value: 'obsidian-vault' }
          ]
        }
      ]
      scale: {
        minReplicas: 0   // Scale to zero when idle → cost savings
        maxReplicas: 3
      }
    }
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────
output storageAccountName string = storageAccount.name
output searchServiceEndpoint string = 'https://${searchServiceName}.search.windows.net'
output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
