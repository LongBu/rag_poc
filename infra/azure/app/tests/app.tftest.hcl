mock_provider "azurerm" {
  mock_resource "azurerm_user_assigned_identity" {
    defaults = {
      id           = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/private-azure-chat/providers/Microsoft.ManagedIdentity/userAssignedIdentities/private-azure-chat-runtime"
      client_id    = "00000000-0000-0000-0000-000000000005"
      principal_id = "00000000-0000-0000-0000-000000000006"
    }
  }
  mock_resource "azurerm_container_app_environment" {
    defaults = {
      id             = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/private-azure-chat/providers/Microsoft.App/managedEnvironments/private-azure-chat-environment"
      default_domain = "example.eastus2.azurecontainerapps.io"
    }
  }
  mock_resource "azurerm_container_app" {
    defaults = { ingress = { fqdn = "private-azure-chat.example.eastus2.azurecontainerapps.io" } }
  }
}
mock_provider "azuread" {}
override_resource {
  target = azuread_application_registration.api
  values = {
    id        = "/applications/00000000-0000-0000-0000-000000000011"
    client_id = "00000000-0000-0000-0000-000000000012"
  }
}
override_resource {
  target = azuread_application_registration.spa
  values = {
    id        = "/applications/00000000-0000-0000-0000-000000000021"
    client_id = "00000000-0000-0000-0000-000000000022"
  }
}
variables {
  subscription_id           = "00000000-0000-0000-0000-000000000001"
  tenant_id                 = "00000000-0000-0000-0000-000000000002"
  owner_object_id           = "00000000-0000-0000-0000-000000000003"
  directory_admin_object_id = "00000000-0000-0000-0000-000000000004"
  resource_group_name       = "private-azure-chat"
  model_account_id          = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/private-azure-chat/providers/Microsoft.CognitiveServices/accounts/private-azure-chat-00000000"
  model_endpoint            = "https://private-azure-chat-00000000.openai.azure.com/"
  model_deployment          = "gpt-5-mini"
}
run "bootstrap" {
  command = apply
  assert {
    condition     = length(azurerm_container_app.chat) == 0 && length(azurerm_container_app_environment.chat) == 0 && output.app_url == null
    error_message = "Default bootstrap must not deploy hosting."
  }
  assert {
    condition     = azurerm_role_assignment.inference.scope == var.model_account_id && azurerm_role_assignment.inference.role_definition_name == "Cognitive Services OpenAI User" && azurerm_role_assignment.inference.principal_id == azurerm_user_assigned_identity.runtime.principal_id && azurerm_user_assigned_identity.runtime.resource_group_name == var.resource_group_name
    error_message = "Runtime RBAC belongs to app state and must be scoped to the shared model account."
  }
}
run "activate" {
  command = apply
  variables {
    deploy_app   = true
    image_digest = "ghcr.io/example/chat@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  assert {
    condition     = azurerm_container_app_environment.chat[0].logs_destination == "" && azurerm_container_app_environment.chat[0].log_analytics_workspace_id == null && one(azurerm_container_app_environment.chat[0].workload_profile).workload_profile_type == "Consumption"
    error_message = "Use Consumption with live-only logging and no paid log workspace."
  }
  assert {
    condition     = azurerm_container_app.chat[0].revision_mode == "Single" && azurerm_container_app.chat[0].template[0].min_replicas == 0 && azurerm_container_app.chat[0].template[0].max_replicas == 1 && azurerm_container_app.chat[0].template[0].container[0].cpu == 0.25 && azurerm_container_app.chat[0].template[0].container[0].memory == "0.5Gi"
    error_message = "Keep reviewed CPU/memory and zero-to-one replicas in a single active revision."
  }
  assert {
    condition     = azurerm_container_app.chat[0].ingress[0].external_enabled && !azurerm_container_app.chat[0].ingress[0].allow_insecure_connections && azurerm_container_app.chat[0].ingress[0].target_port == 8000 && one(azurerm_container_app.chat[0].ingress[0].traffic_weight).latest_revision && one(azurerm_container_app.chat[0].ingress[0].traffic_weight).percentage == 100
    error_message = "Expose only HTTPS to the current app revision on port 8000."
  }
  assert {
    condition     = azurerm_container_app.chat[0].template[0].container[0].image == var.image_digest && length(azurerm_container_app.chat[0].registry) == 0 && length(azurerm_container_app.chat[0].secret) == 0 && azurerm_container_app.chat[0].identity[0].type == "UserAssigned" && toset(azurerm_container_app.chat[0].identity[0].identity_ids) == toset([azurerm_user_assigned_identity.runtime.id])
    error_message = "Pull a public immutable digest anonymously, without registry secrets; use managed identity only for inference."
  }
  assert {
    condition     = azurerm_container_app.chat[0].template[0].container[0].readiness_probe[0].path == "/ready" && azurerm_container_app.chat[0].template[0].container[0].readiness_probe[0].port == 8000 && azurerm_container_app.chat[0].template[0].container[0].readiness_probe[0].transport == "HTTP" && azurerm_container_app.chat[0].template[0].container[0].startup_probe[0].failure_count_threshold == 30
    error_message = "Use inference-free HTTP readiness and bounded startup allowance."
  }
  assert {
    condition     = { for e in azurerm_container_app.chat[0].template[0].container[0].env : e.name => e.value } == local.environment && alltrue([for e in azurerm_container_app.chat[0].template[0].container[0].env : e.secret_name == null]) && local.environment.AZURE_AUTH_MODE == "managed_identity" && local.environment.AZURE_CLIENT_ID == output.runtime_client_id && local.environment.FRONTEND_ORIGIN == output.app_url && local.environment.AZURE_OPENAI_ENDPOINT == var.model_endpoint
    error_message = "Only the exact public runtime settings may enter the container environment."
  }
}
run "entra_contract" {
  command = apply
  assert {
    condition     = azuread_application_registration.api.sign_in_audience == "AzureADMyOrg" && azuread_application_registration.spa.sign_in_audience == "AzureADMyOrg" && azuread_application_registration.api.requested_access_token_version == 2 && !azuread_application_registration.spa.implicit_access_token_issuance_enabled && !azuread_application_registration.spa.implicit_id_token_issuance_enabled
    error_message = "Use single-tenant v2 registrations without implicit token grants."
  }
  assert {
    condition     = azuread_service_principal.api.client_id == output.api_client_id && azuread_service_principal.spa.client_id == output.spa_client_id && azuread_application_identifier_uri.api.identifier_uri == "api://${output.api_client_id}" && azuread_application_permission_scope.query.value == "query" && output.api_scope == "api://${output.api_client_id}/query"
    error_message = "API service principal, identifier and delegated scope must agree with runtime config."
  }
  assert {
    condition     = azuread_application_pre_authorized.spa.application_id == azuread_application_registration.api.id && azuread_application_pre_authorized.spa.authorized_client_id == output.spa_client_id && azuread_application_pre_authorized.spa.permission_ids == toset([azuread_application_permission_scope.query.scope_id]) && azuread_application_api_access.query.scope_ids == toset([azuread_application_permission_scope.query.scope_id]) && azuread_application_api_access.query.role_ids == null
    error_message = "Preauthorize only this SPA and its delegated query scope, without app-only roles."
  }
  assert {
    condition     = length(azuread_application_redirect_uris.spa) == 0 && azuread_application_registration.spa.logout_url == null && azuread_application_owner.api.owner_object_id == var.directory_admin_object_id && azuread_application_owner.spa.owner_object_id == var.directory_admin_object_id
    error_message = "Bootstrap identities have no placeholder callback URLs and retain the directory administrator as owner."
  }
}
run "exact_callbacks" {
  command = apply
  variables {
    deploy_app   = true
    image_digest = "ghcr.io/example/chat@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  assert {
    condition     = azuread_application_redirect_uris.spa[0].type == "SPA" && azuread_application_redirect_uris.spa[0].redirect_uris == toset(["${output.app_url}/"]) && azuread_application_registration.spa.logout_url == "${output.app_url}/" && output.redirect_uri == "${output.app_url}/"
    error_message = "Register only the exact generated HTTPS root for PKCE callback and logout."
  }
}

run "reject_subscription_id_0" {
  command = plan
  variables {
    subscription_id = "bad"
  }
  expect_failures = [var.subscription_id]
}

run "reject_tenant_id_1" {
  command = plan
  variables {
    tenant_id = "bad"
  }
  expect_failures = [var.tenant_id]
}

run "reject_owner_object_id_2" {
  command = plan
  variables {
    owner_object_id = "bad"
  }
  expect_failures = [var.owner_object_id]
}

run "reject_directory_admin_object_id_3" {
  command = plan
  variables {
    directory_admin_object_id = "bad"
  }
  expect_failures = [var.directory_admin_object_id]
}

run "reject_name_4" {
  command = plan
  variables {
    name = "UPPER"
  }
  expect_failures = [var.name]
}

run "reject_location_5" {
  command = plan
  variables {
    location = "uksouth"
  }
  expect_failures = [var.location]
}

run "reject_resource_group_name_6" {
  command = plan
  variables {
    resource_group_name = "bad/group"
  }
  expect_failures = [var.resource_group_name]
}

run "reject_model_account_id_7" {
  command = plan
  variables {
    model_account_id = "/subscriptions/00000000-0000-0000-0000-000000000099/resourceGroups/private-azure-chat/providers/Microsoft.CognitiveServices/accounts/other"
  }
  expect_failures = [var.model_account_id]
}

run "reject_model_endpoint_8" {
  command = plan
  variables {
    model_endpoint = "https://other.openai.azure.com/"
  }
  expect_failures = [var.model_endpoint]
}

run "reject_model_deployment_9" {
  command = plan
  variables {
    model_deployment = "gpt-5-nano"
  }
  expect_failures = [var.model_deployment]
}

run "reject_image_digest_10" {
  command = plan
  variables {
    image_digest = "ghcr.io/example/chat:latest"
  }
  expect_failures = [var.image_digest]
}

run "reject_image_digest_11" {
  command = plan
  variables {
    image_digest = "ghcr.io/example/chat@sha256:bad"
  }
  expect_failures = [var.image_digest]
}

run "reject_image_digest_12" {
  command = plan
  variables {
    image_digest = "https://user:password@ghcr.io/example/chat"
  }
  expect_failures = [var.image_digest]
}

run "activation_requires_digest" {
  command = plan
  variables {
    deploy_app = true
  }
  expect_failures = [var.image_digest]
}
run "reject_group_scope_lookalike" {
  command = plan
  variables {
    resource_group_name = "private.azure.chat"
  }
  expect_failures = [var.model_account_id]
}
run "reject_container_name_length" {
  command = plan
  variables {
    name = "this-name-is-longer-than-thirty-two-characters"
  }
  expect_failures = [var.name]
}
