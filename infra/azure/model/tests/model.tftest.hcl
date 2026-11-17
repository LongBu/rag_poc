mock_provider "azurerm" {
  mock_resource "azurerm_resource_group" {
    defaults = { id = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/private-azure-chat" }
  }
  mock_resource "azurerm_cognitive_account" {
    defaults = {
      id       = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/private-azure-chat/providers/Microsoft.CognitiveServices/accounts/private-azure-chat-00000000"
      endpoint = "https://private-azure-chat-00000000.openai.azure.com/"
    }
  }
}
variables {
  subscription_id     = "00000000-0000-0000-0000-000000000001"
  tenant_id           = "00000000-0000-0000-0000-000000000002"
  developer_object_id = "00000000-0000-0000-0000-000000000003"
  budget_email        = "owner@example.com"
  budget_start_date   = "2026-11-01T00:00:00Z"
  billing_currency    = "USD"
}
run "model_resources" {
  command = apply
  assert {
    condition     = azurerm_resource_group.chat.name == "private-azure-chat" && azurerm_resource_group.chat.location == "eastus2"
    error_message = "Model stage must own its dedicated US resource group."
  }
  assert {
    condition     = !azurerm_cognitive_account.chat.local_auth_enabled && azurerm_cognitive_account.chat.kind == "OpenAI" && azurerm_cognitive_account.chat.sku_name == "S0"
    error_message = "Use a keyless dedicated OpenAI account."
  }
  assert {
    condition     = azurerm_cognitive_deployment.chat.model[0].name == "gpt-5-mini" && azurerm_cognitive_deployment.chat.model[0].version == "2025-08-07" && azurerm_cognitive_deployment.chat.sku[0].name == "GlobalStandard" && azurerm_cognitive_deployment.chat.sku[0].capacity == 10 && azurerm_cognitive_deployment.chat.version_upgrade_option == "NoAutoUpgrade"
    error_message = "Pin the reviewed model/version and pay-per-token capacity without automatic fallback."
  }
  assert {
    condition     = azurerm_role_assignment.developer.scope == azurerm_cognitive_account.chat.id && azurerm_role_assignment.developer.role_definition_name == "Cognitive Services OpenAI User" && azurerm_role_assignment.developer.principal_id == var.developer_object_id
    error_message = "Developer inference RBAC must be account-scoped."
  }
  assert {
    condition     = azurerm_consumption_budget_resource_group.monthly.resource_group_id == azurerm_resource_group.chat.id && azurerm_consumption_budget_resource_group.monthly.amount == 5 && azurerm_consumption_budget_resource_group.monthly.time_grain == "Monthly" && azurerm_consumption_budget_resource_group.monthly.time_period[0].start_date == var.budget_start_date
    error_message = "The monthly budget must cover the shared project group."
  }
  assert {
    condition     = toset([for n in azurerm_consumption_budget_resource_group.monthly.notification : n.threshold]) == toset([50, 80, 100]) && alltrue([for n in azurerm_consumption_budget_resource_group.monthly.notification : n.enabled && n.threshold_type == "Actual" && n.operator == "GreaterThanOrEqualTo" && toset(n.contact_emails) == toset([var.budget_email])])
    error_message = "Require actual 50/80/100 email alerts."
  }
}
run "public_outputs" {
  command = apply
  assert {
    condition     = output.model_account_id == azurerm_cognitive_account.chat.id && output.model_endpoint == azurerm_cognitive_account.chat.endpoint && output.resource_group_id == azurerm_resource_group.chat.id && output.model_deployment == "gpt-5-mini" && output.model_version == "2025-08-07" && output.tenant_id == var.tenant_id && output.deployment_type == "GlobalStandard" && output.capacity == 10 && output.budget_id == azurerm_consumption_budget_resource_group.monthly.id
    error_message = "Expose public model/app handoff values without keys."
  }
}

run "reject_subscription_id_0" {
  command = plan
  variables {
    subscription_id = "------------------------------------"
  }
  expect_failures = [var.subscription_id]
}

run "reject_tenant_id_1" {
  command = plan
  variables {
    tenant_id = "invalid"
  }
  expect_failures = [var.tenant_id]
}

run "reject_developer_object_id_2" {
  command = plan
  variables {
    developer_object_id = "not-an-object-id"
  }
  expect_failures = [var.developer_object_id]
}

run "reject_name_3" {
  command = plan
  variables {
    name = "UPPERCASE"
  }
  expect_failures = [var.name]
}

run "reject_location_4" {
  command = plan
  variables {
    location = "uksouth"
  }
  expect_failures = [var.location]
}

run "reject_capacity_5" {
  command = plan
  variables {
    capacity = 0
  }
  expect_failures = [var.capacity]
}

run "reject_capacity_6" {
  command = plan
  variables {
    capacity = 1001
  }
  expect_failures = [var.capacity]
}

run "reject_capacity_7" {
  command = plan
  variables {
    capacity = 1.5
  }
  expect_failures = [var.capacity]
}

run "reject_budget_amount_8" {
  command = plan
  variables {
    budget_amount = 0
  }
  expect_failures = [var.budget_amount]
}

run "reject_budget_amount_9" {
  command = plan
  variables {
    budget_amount = -1
  }
  expect_failures = [var.budget_amount]
}

run "reject_billing_currency_10" {
  command = plan
  variables {
    billing_currency = "EUR"
  }
  expect_failures = [var.billing_currency]
}

run "reject_budget_email_11" {
  command = plan
  variables {
    budget_email = "not an email"
  }
  expect_failures = [var.budget_email]
}

run "reject_budget_email_12" {
  command = plan
  variables {
    budget_email = "owner@example.com\nextra"
  }
  expect_failures = [var.budget_email]
}

run "reject_budget_start_date_13" {
  command = plan
  variables {
    budget_start_date = "2026-02-30T00:00:00Z"
  }
  expect_failures = [var.budget_start_date]
}

run "reject_budget_start_date_14" {
  command = plan
  variables {
    budget_start_date = "2026-11-02T00:00:00Z"
  }
  expect_failures = [var.budget_start_date]
}
