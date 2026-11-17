locals {
  model_name    = "gpt-5-mini"
  model_version = "2025-08-07"
  account_name  = "${var.name}-${substr(replace(var.subscription_id, "-", ""), 0, 8)}"
}
resource "azurerm_resource_group" "chat" {
  name     = var.name
  location = var.location
  tags     = { Project = var.name }
}
resource "azurerm_consumption_budget_resource_group" "monthly" {
  name              = "${var.name}-monthly"
  resource_group_id = azurerm_resource_group.chat.id
  amount            = var.budget_amount
  time_grain        = "Monthly"
  time_period {
    start_date = var.budget_start_date
  }
  dynamic "notification" {
    for_each = toset([50, 80, 100])
    content {
      enabled        = true
      threshold      = notification.value
      operator       = "GreaterThanOrEqualTo"
      threshold_type = "Actual"
      contact_emails = [var.budget_email]
    }
  }
}
resource "azurerm_cognitive_account" "chat" {
  name                          = local.account_name
  custom_subdomain_name         = local.account_name
  resource_group_name           = azurerm_resource_group.chat.name
  location                      = azurerm_resource_group.chat.location
  kind                          = "OpenAI"
  sku_name                      = "S0"
  local_auth_enabled            = false
  public_network_access_enabled = true
  tags                          = azurerm_resource_group.chat.tags
  depends_on                    = [azurerm_consumption_budget_resource_group.monthly]
}
resource "azurerm_cognitive_deployment" "chat" {
  name                   = local.model_name
  cognitive_account_id   = azurerm_cognitive_account.chat.id
  version_upgrade_option = "NoAutoUpgrade"
  model {
    format  = "OpenAI"
    name    = local.model_name
    version = local.model_version
  }
  sku {
    name     = "GlobalStandard"
    capacity = var.capacity
  }
}
resource "azurerm_role_assignment" "developer" {
  scope                = azurerm_cognitive_account.chat.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = var.developer_object_id
  principal_type       = "User"
}
