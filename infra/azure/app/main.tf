resource "azurerm_user_assigned_identity" "runtime" {
  name                = "${var.name}-runtime"
  resource_group_name = var.resource_group_name
  location            = var.location
}
resource "azurerm_role_assignment" "inference" {
  scope                = var.model_account_id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.runtime.principal_id
  principal_type       = "ServicePrincipal"
}
resource "azurerm_container_app_environment" "chat" {
  count               = var.deploy_app ? 1 : 0
  name                = "${var.name}-environment"
  resource_group_name = var.resource_group_name
  location            = var.location
  # Empty destination means live streaming only in the pinned provider.
  logs_destination = ""
  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}
locals {
  origin = var.deploy_app ? "https://${var.name}.${azurerm_container_app_environment.chat[0].default_domain}" : null
  environment = {
    AZURE_TENANT_ID          = var.tenant_id
    AZURE_CLIENT_ID          = azurerm_user_assigned_identity.runtime.client_id
    AZURE_AUTH_MODE          = "managed_identity"
    AZURE_OPENAI_ENDPOINT    = var.model_endpoint
    AZURE_OPENAI_DEPLOYMENT  = var.model_deployment
    AZURE_OPENAI_API_VERSION = "2025-04-01-preview"
    ENTRA_API_CLIENT_ID      = azuread_application_registration.api.client_id
    ENTRA_SPA_CLIENT_ID      = azuread_application_registration.spa.client_id
    ENTRA_OWNER_OBJECT_ID    = var.owner_object_id
    FRONTEND_ORIGIN          = local.origin
  }
}
resource "azurerm_container_app" "chat" {
  count                        = var.deploy_app ? 1 : 0
  name                         = var.name
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.chat[0].id
  workload_profile_name        = "Consumption"
  revision_mode                = "Single"
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.runtime.id]
  }
  ingress {
    external_enabled           = true
    allow_insecure_connections = false
    target_port                = 8000
    transport                  = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
  template {
    min_replicas = 0
    max_replicas = 1
    http_scale_rule {
      name                = "http"
      concurrent_requests = "1"
    }
    container {
      name   = "chat"
      image  = var.image_digest
      cpu    = 0.25
      memory = "0.5Gi"
      dynamic "env" {
        for_each = local.environment
        content {
          name  = env.key
          value = env.value
        }
      }
      readiness_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/ready"
        interval_seconds        = 5
        timeout                 = 2
        failure_count_threshold = 3
      }
      startup_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/ready"
        interval_seconds        = 5
        timeout                 = 2
        failure_count_threshold = 30
      }
    }
  }
  depends_on = [azurerm_role_assignment.inference, azuread_application_pre_authorized.spa]
  lifecycle {
    postcondition {
      condition     = "https://${self.ingress[0].fqdn}" == local.origin
      error_message = "Generated app origin differs from the configured same-origin URL."
    }
  }
}
