variable "subscription_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "Supply the selected subscription UUID."
  }
}
variable "tenant_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.tenant_id))
    error_message = "Supply the selected Entra tenant UUID."
  }
}
variable "developer_object_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.developer_object_id))
    error_message = "Supply the provisioning developer's Entra object UUID, not the chat owner."
  }
}
variable "name" {
  type    = string
  default = "private-azure-chat"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,39}$", var.name))
    error_message = "Use 3-40 lowercase letters, digits, or hyphens, starting with a letter."
  }
}
variable "location" {
  type    = string
  default = "eastus2"
  validation {
    condition     = contains(["eastus2", "eastus", "westus3", "centralus", "southcentralus", "northcentralus", "westus", "westus2"], var.location)
    error_message = "Choose an explicitly verified US resource region."
  }
}
variable "capacity" {
  type        = number
  default     = 10
  description = "Thousands of TPM; quota allocation, not provisioned throughput or a spending limit."
  validation {
    condition     = var.capacity >= 1 && var.capacity <= 1000 && floor(var.capacity) == var.capacity
    error_message = "Capacity must be an integer from 1 to the verified 1,000-unit quota."
  }
}
variable "budget_amount" {
  type    = number
  default = 5
  validation {
    condition     = var.budget_amount > 0
    error_message = "Budget must be positive."
  }
}
variable "billing_currency" {
  type = string
  validation {
    condition     = var.billing_currency == "USD"
    error_message = "This deployment requires verified USD billing; agree another currency/amount before changing it."
  }
}
variable "budget_email" {
  type      = string
  sensitive = true
  validation {
    condition     = can(regex("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$", var.budget_email))
    error_message = "Supply one valid budget notification email address."
  }
}
variable "budget_start_date" {
  type        = string
  description = "First day of the current UTC month, e.g. 2026-11-01T00:00:00Z; retain after apply."
  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-01T00:00:00Z$", var.budget_start_date)) && can(formatdate("YYYY", var.budget_start_date))
    error_message = "Budget start must be a valid first-of-month UTC midnight timestamp."
  }
}
