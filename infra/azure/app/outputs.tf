output "tenant_id" {
  value = var.tenant_id
}
output "api_client_id" {
  value = azuread_application_registration.api.client_id
}
output "spa_client_id" {
  value = azuread_application_registration.spa.client_id
}
output "api_scope" {
  value = "api://${azuread_application_registration.api.client_id}/query"
}
output "runtime_client_id" {
  value = azurerm_user_assigned_identity.runtime.client_id
}
output "runtime_principal_id" {
  value = azurerm_user_assigned_identity.runtime.principal_id
}
output "app_url" {
  value = var.deploy_app ? "https://${azurerm_container_app.chat[0].ingress[0].fqdn}" : null
}
output "redirect_uri" {
  value = var.deploy_app ? one(azuread_application_redirect_uris.spa[0].redirect_uris) : null
}
