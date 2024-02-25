provider "azurerm" {
  features {}
}
# Storage Account
resource "random_string" "random_suffix" {
  length  = 8
  special = false
  upper   = false
}
# Resource Group
resource "azurerm_resource_group" "resource_group" {
  name     = var.resource_group_name
  location = "East US"  # Replace with your location
}

# Event Hub Namespace
resource "azurerm_eventhub_namespace" "eventhub_namespace" {
  name = var.eventhub_namespace
  location = azurerm_resource_group.resource_group.location
  resource_group_name = var.resource_group_name
  sku = "Standard"
  capacity = 1
  auto_inflate_enabled = true
  maximum_throughput_units = 20
}

# Null resource to enforce ordering
resource "null_resource" "wait_for_namespace" {
  depends_on = [azurerm_eventhub_namespace.eventhub_namespace]
}

# Data source for authorization rule
data "azurerm_eventhub_namespace_authorization_rule" "example" {
  name                = "RootManageSharedAccessKey"
  namespace_name      = azurerm_eventhub_namespace.eventhub_namespace.name
  resource_group_name = var.resource_group_name

  # Enforce dependency via null_resource
  depends_on = [null_resource.wait_for_namespace]
}

locals {
  storage_account_name = "fa${random_string.random_suffix.result}"
  function_app_name    = "funcapp${random_string.random_suffix.result}"
  app_service_plan_name = "asp${random_string.random_suffix.result}"
  app_insights_name    = "ai${random_string.random_suffix.result}"
  eventhub_connection_string = "Endpoint=sb://${azurerm_eventhub_namespace.eventhub_namespace.name}.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=${data.azurerm_eventhub_namespace_authorization_rule.example.primary_key}"
}

resource "azurerm_storage_account" "storage_account" {
  name                     = local.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = azurerm_resource_group.resource_group.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  access_tier              = "Hot"
  enable_https_traffic_only = true
}

# Blob Container
resource "azurerm_storage_container" "storage_container" {
  name                  = var.failed_log_backup_container
  storage_account_name  = azurerm_storage_account.storage_account.name
  container_access_type = "private"
}

# Event Hub
resource "azurerm_eventhub" "event_hub" {
  name                = var.eventhub_logs_name
  namespace_name      = azurerm_eventhub_namespace.eventhub_namespace.name
  resource_group_name = var.resource_group_name
  partition_count     = 32
  message_retention   = 7
}

# App Service Plan
resource "azurerm_service_plan" "app_service_plan" {
  name                = local.app_service_plan_name
  location            = azurerm_resource_group.resource_group.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = "Y1"
}

# Function App
resource "azurerm_linux_function_app" "function_app" {
  name                       = local.function_app_name
  location                   = azurerm_resource_group.resource_group.location
  resource_group_name        = var.resource_group_name

  service_plan_id            = azurerm_service_plan.app_service_plan.id
  storage_account_name       = azurerm_storage_account.storage_account.name
  storage_account_access_key = azurerm_storage_account.storage_account.primary_access_key

  site_config {
    application_insights_connection_string = azurerm_application_insights.app_insights.connection_string
    application_stack {
      python_version = "3.11"
    }

  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME" = "python"
    "FUNCTIONS_EXTENSION_VERSION" = "~4"
    "AzureWebJobsEventHubConnectionString" = local.eventhub_connection_string
    "AzureWebJobsStorage" = azurerm_storage_account.storage_account.primary_connection_string
    "WEBSITE_RUN_FROM_PACKAGE" = "https://logzioblobtrigger.blob.core.windows.net/eventhub/logzio_function-v0.0.1.zip"
    "LogzioURL" = var.logzio_url
    "LogzioToken" = var.logzio_token
    "EventhubLogsName" = var.eventhub_logs_name
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.app_insights.instrumentation_key
    "AZURE_STORAGE_CONTAINER_NAME" = azurerm_storage_container.storage_container.name
    "THREAD_COUNT" = var.thread_count
    "BUFFER_SIZE" = var.buffer_size
    "INTERVAL_TIME" = var.interval_time
    "MAX_TRIES" = var.max_tries
    "LOG_TYPE" = var.log_type
  }
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "log_analytics_workspace" {
  name                = var.log_analytics_workspace_name
  location            = azurerm_resource_group.resource_group.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
}

# Application Insights
resource "azurerm_application_insights" "app_insights" {
  name                = local.app_insights_name
  location            = azurerm_resource_group.resource_group.location
  resource_group_name = var.resource_group_name
  application_type    = "web"
}
