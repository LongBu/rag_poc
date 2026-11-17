resource "azuread_application_registration" "api" {
  display_name                           = "${var.name}-api"
  sign_in_audience                       = "AzureADMyOrg"
  requested_access_token_version         = 2
  implicit_access_token_issuance_enabled = false
  implicit_id_token_issuance_enabled     = false
}
resource "azuread_application_registration" "spa" {
  display_name                           = "${var.name}-spa"
  sign_in_audience                       = "AzureADMyOrg"
  requested_access_token_version         = 2
  implicit_access_token_issuance_enabled = false
  implicit_id_token_issuance_enabled     = false
  logout_url                             = var.deploy_app ? "${local.origin}/" : null
}
resource "azuread_application_owner" "api" {
  application_id  = azuread_application_registration.api.id
  owner_object_id = var.directory_admin_object_id
}
resource "azuread_application_owner" "spa" {
  application_id  = azuread_application_registration.spa.id
  owner_object_id = var.directory_admin_object_id
}
resource "azuread_service_principal" "api" {
  client_id = azuread_application_registration.api.client_id
  owners    = [var.directory_admin_object_id]
}
resource "azuread_service_principal" "spa" {
  client_id = azuread_application_registration.spa.client_id
  owners    = [var.directory_admin_object_id]
}
resource "azuread_application_identifier_uri" "api" {
  application_id = azuread_application_registration.api.id
  identifier_uri = "api://${azuread_application_registration.api.client_id}"
}
resource "azuread_application_permission_scope" "query" {
  application_id             = azuread_application_registration.api.id
  scope_id                   = uuidv5("url", "${azuread_application_registration.api.client_id}/query")
  value                      = "query"
  type                       = "User"
  admin_consent_description  = "Send owner-authorized chat queries."
  admin_consent_display_name = "Query chat"
  user_consent_description   = "Send chat queries as you; the API separately restricts access to its owner."
  user_consent_display_name  = "Query chat"
}
resource "azuread_application_api_access" "query" {
  application_id = azuread_application_registration.spa.id
  api_client_id  = azuread_application_registration.api.client_id
  scope_ids      = [azuread_application_permission_scope.query.scope_id]
}
resource "azuread_application_pre_authorized" "spa" {
  application_id       = azuread_application_registration.api.id
  authorized_client_id = azuread_application_registration.spa.client_id
  permission_ids       = [azuread_application_permission_scope.query.scope_id]
}
resource "azuread_application_redirect_uris" "spa" {
  count          = var.deploy_app ? 1 : 0
  application_id = azuread_application_registration.spa.id
  type           = "SPA"
  redirect_uris  = ["https://${azurerm_container_app.chat[0].ingress[0].fqdn}/"]
}
