variable "name" {
  description = "Unique lowercase prefix for application resources."
  type        = string
  default     = "private-bedrock-chat"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,29}$", var.name))
    error_message = "Use 3-30 lowercase letters, digits, or hyphens, starting with a letter."
  }
}

variable "trusted_principal_arn" {
  description = "Supply through TF_VAR_trusted_principal_arn: stable same-account IAM user/role ARN, never an STS session ARN."
  type        = string
  sensitive   = true
  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:(role|user)/[A-Za-z0-9+=,.@_/-]+$", var.trusted_principal_arn))
    error_message = "Supply a stable AWS IAM user/role ARN."
  }
}

variable "budget_email" {
  description = "Supply through TF_VAR_budget_email: recipient for delayed budget notifications."
  type        = string
  sensitive   = true
  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.budget_email))
    error_message = "Supply a valid budget notification email."
  }
}

variable "monthly_budget_usd" {
  description = "Notification threshold, not a spending cap."
  type        = number
  default     = 5
  validation {
    condition     = var.monthly_budget_usd > 0
    error_message = "The budget must be positive."
  }
}

variable "owner_sub" {
  description = "Immutable Cognito owner subject; empty initially to deny all queries."
  type        = string
  default     = ""
  validation {
    condition     = var.owner_sub == "" || can(regex("^[0-9a-fA-F-]{36}$", var.owner_sub))
    error_message = "Use an empty string or the owner's immutable Cognito subject."
  }
}
