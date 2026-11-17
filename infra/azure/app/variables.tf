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
variable "name" {
  type    = string
  default = "private-azure-chat"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}[a-z0-9]$", var.name)) && !strcontains(var.name, "--")
    error_message = "Use 3-32 lowercase letters, digits or single hyphens, starting with a letter and ending with a letter or digit."
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
variable "owner_object_id" {
  type        = string
  description = "Chat owner object ID in the selected tenant."
  validation {
    condition     = can(regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", var.owner_object_id))
    error_message = "Supply a lowercase Entra object UUID."
  }
}
variable "directory_admin_object_id" {
  type        = string
  description = "Object ID of the user administering these app registrations."
  validation {
    condition     = can(regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", var.directory_admin_object_id))
    error_message = "Supply a lowercase Entra object UUID."
  }
}
variable "resource_group_name" {
  type        = string
  description = "Existing model-root resource group; never recreated by this root."
  validation {
    condition     = can(regex("^[a-zA-Z0-9_.()-]{1,90}$", var.resource_group_name)) && !endswith(var.resource_group_name, ".")
    error_message = "Supply the model root resource_group_name."
  }
}
variable "model_account_id" {
  type = string
  validation {
    condition     = startswith(var.model_account_id, "/subscriptions/${var.subscription_id}/resourceGroups/${var.resource_group_name}/providers/Microsoft.CognitiveServices/accounts/") && can(regex("^/subscriptions/[0-9a-fA-F-]+/resourceGroups/[^/]+/providers/Microsoft[.]CognitiveServices/accounts/[a-zA-Z0-9-]+$", var.model_account_id))
    error_message = "Model account must belong to the selected subscription and shared group."
  }
}
variable "model_endpoint" {
  type = string
  validation {
    condition     = can(regex("^https://[a-z0-9][a-z0-9-]{1,62}[.]openai[.]azure[.]com/$", var.model_endpoint)) && var.model_endpoint == "https://${basename(var.model_account_id)}.openai.azure.com/"
    error_message = "Supply the matching model-root account endpoint."
  }
}
variable "model_deployment" {
  type = string
  validation {
    condition     = var.model_deployment == "gpt-5-mini"
    error_message = "Use the verified GPT-5 mini deployment."
  }
}
variable "deploy_app" {
  type        = bool
  default     = false
  description = "Enable hosting only after reviewing costs/plan and verifying the anonymous image digest."
}
variable "image_digest" {
  type    = string
  default = ""
  validation {
    condition     = var.image_digest == "" ? !var.deploy_app : can(regex("^ghcr[.]io/[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9._/-]*@sha256:[a-f0-9]{64}$", var.image_digest))
    error_message = "Activation requires a public GHCR image pinned by sha256 digest; tags and credentials are forbidden."
  }
}
