# Spec Delta

## Purpose

Make Azure experimentation costs reviewable before each deployment stage and provide configurable resource-group budget notifications for the owner-operated chat application.

## ADDED Requirements

### Requirement: Dated Azure cost estimate
The project SHALL document sourced USD model rates and hosting, registry, egress, identity, and monitoring assumptions before deployment. Estimates SHALL cover 100, 1,000, and 10,000 requests with declared input/history sizes and 512 completion tokens, include reasoning and rebilled history, and distinguish gross charges, verified recurring allowances, and promotional credits.

#### Scenario: Workload comparison
- **WHEN** the owner reads the cost guide
- **THEN** the token formula, verified public GHCR pricing, compute assumptions, sample arithmetic, date, sources, and exclusions allow comparison with the USD 5 budget

#### Scenario: Low usage
- **WHEN** the application is idle or has few model requests
- **THEN** the estimate identifies any remaining Azure idle charges and reports GitHub registry/build pricing separately without assuming perpetual free service

### Requirement: Cost-first US resource selection
The workflow SHALL compare verified total operating costs across eligible US resource regions and pay-per-token deployment types, starting with Global Standard. Global inference processing SHALL be acceptable. The selected region SHALL satisfy model availability and quota constraints, and its model, compute, and egress assumptions SHALL be recorded before provisioning.

#### Scenario: Select a deployment region
- **WHEN** preflight identifies eligible US resource regions and current prices
- **THEN** the workflow records a cost-based selection without requiring East US 2 or US-only inference processing

### Requirement: Scoped monthly budget alerts
Terraform SHALL create a positive monthly resource-group budget defaulting to USD 5 for USD-billed subscriptions and actual-cost email thresholds at 50%, 80%, and 100%. The scope SHALL include the model and all project hosting resources across deployment stages. Notification delay and continued spending after alerts SHALL be explained.

#### Scenario: Budget before model probe
- **WHEN** a billable access probe is authorized
- **THEN** the budget is already provisioned, its recipient/scope/thresholds are verified, and the user knows the probe may incur charges

#### Scenario: Budget threshold crossed
- **WHEN** actual evaluated cost exceeds a configured threshold
- **THEN** Cost Management is configured to notify the supplied email without claiming resources will stop

### Requirement: Billing currency and offer validation
Preflight SHALL identify billing currency, Cost Management/budget support, and relevant credit/free-grant eligibility for the subscription. USD 5 SHALL NOT be silently represented as five units of another currency. Unsupported budget offers or non-USD currency SHALL be reported before deployment and require an explicit compatible budget amount or subscription decision.

#### Scenario: Non-USD subscription
- **WHEN** billing uses another currency
- **THEN** the workflow records the agreed local-currency equivalent and conversion date before creating the budget

#### Scenario: Credits are unknown
- **WHEN** credit eligibility cannot be verified
- **THEN** estimates assume zero promotional credit and retain gross-cost calculations

### Requirement: Deployment stage cost gate
The workflow SHALL check model access before application hosting and present each stage's intended resources and costs in a fresh plan. A failed inference test SHALL leave hosting undeployed and provide cleanup instructions. Cost estimates SHALL distinguish Azure-budget coverage from external GitHub registry/build charges and disclose any idle baseline before application-stage approval.

#### Scenario: Account restriction
- **WHEN** the minimal Azure model request is rejected
- **THEN** the workflow records the error and allows reviewed model-stage cleanup while image publication and application hosting remain pending

#### Scenario: Public registry costs and budget scope
- **WHEN** the application uses public GHCR images
- **THEN** the cost guide records dated registry pricing and any build charges, explains that GitHub usage is outside the Azure resource-group budget, and includes no Azure Container Registry resource fee

### Requirement: Bounded usage controls
The deployed application SHALL bound completion tokens, per-process concurrency/rate, retries, timeouts, and normal steady-state replicas. Documentation SHALL distinguish these controls from monthly spending enforcement and explain cold-start, revision overlap, registry, and logging costs.

#### Scenario: Burst or provider failure
- **WHEN** a burst exceeds the application's allowance or a provider request fails
- **THEN** the system rejects excess requests or returns a safe failure without unbounded retries or automatically increasing generation limits

### Requirement: Secret-free deployment and retained state
The project SHALL exclude private inputs, credentials, Terraform state/backups, plans, and build output from version control. Deployment instructions SHALL preserve state across partial failures and require fresh plans after changes. Teardown SHALL affect only reviewed managed Azure resources and retain state until removal is verified.

#### Scenario: Partial apply
- **WHEN** an apply fails after creating some resources
- **THEN** the workflow preserves state, diagnoses the specific failure, and generates a new plan without deleting state or forcing a full recreate
