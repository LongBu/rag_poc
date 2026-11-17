output "resource_group_name" {
  value = azurerm_resource_group.chat.name
}
output "resource_group_id" {
  value = azurerm_resource_group.chat.id
}
output "location" {
  value = azurerm_resource_group.chat.location
}
output "model_account_id" {
  value = azurerm_cognitive_account.chat.id
}
output "model_endpoint" {
  value = azurerm_cognitive_account.chat.endpoint
}
output "model_deployment" {
  value = azurerm_cognitive_deployment.chat.name
}
output "model_version" {
  value = local.model_version
}
output "budget_id" {
  value = azurerm_consumption_budget_resource_group.monthly.id
}
output "tenant_id" {
  value = var.tenant_id
}
output "deployment_type" {
  value = azurerm_cognitive_deployment.chat.sku[0].name
}
output "capacity" {
  value = azurerm_cognitive_deployment.chat.sku[0].capacity
}
