# Spec Delta

## Purpose

Make expected Bedrock experimentation costs visible before deployment and provide configurable spending notifications.

## ADDED Requirements

### Requirement: Upfront cost estimate
The system SHALL document dated, sourced USD input/output token rates for the default model and region, the cost formula, and at least three workload examples before deployment. Estimates SHALL assume zero credits, distinguish reference from verified current prices, and include authentication, hosting, API, compute, logging, and recurring resource costs and exclusions such as taxes.

#### Scenario: Estimate experimental usage
- **WHEN** a user reviews the cost guide
- **THEN** they can calculate expected charges from input and output tokens and see assumptions for 100, 1,000, and 10,000 requests, including rebilled conversational history

### Requirement: Configurable budget notifications
Terraform SHALL create a monthly USD cost budget covering Bedrock, Lambda, API Gateway, Cognito, S3, CloudFront, and CloudWatch with a positive configurable amount defaulting to USD 5 and a required email recipient. It SHALL configure actual-cost alerts at 50%, 80%, and 100%, excluding credits and refunds from tracked usage costs.

#### Scenario: Review budget configuration
- **WHEN** the default Terraform plan is reviewed with a valid notification email
- **THEN** it shows a USD 5 monthly cost budget covering the application service set and all three email notification thresholds

#### Scenario: Invalid budget inputs
- **WHEN** the budget is zero or negative, or the notification recipient is absent or malformed
- **THEN** configuration validation rejects the inputs before creating resources

### Requirement: Honest spending and credit limitations
Documentation SHALL explain that budget notifications are delayed alerts rather than a hard cap, token limits apply per request rather than per month, and Free Tier credits are account-specific. It SHALL provide a Billing console credit-verification procedure without assuming a remaining balance.

#### Scenario: Credits are unknown
- **WHEN** no account credit balance has been verified
- **THEN** the guide presents full usage charges and instructions to check credit balance, expiration, and applicability

### Requirement: Application usage safeguards
The application SHALL configure API throttling, bounded Lambda concurrency and timeout, and finite log retention. Documentation SHALL explain their limitations and provide workload estimates with and without applicable recurring free allowances, distinguishing these from promotional credits.

#### Scenario: Review application costs
- **WHEN** the user reviews deployment costs
- **THEN** they can see compute-duration, frontend-traffic, storage, logging, and one-user authentication assumptions in addition to model-token costs

### Requirement: Conversation cost visibility
The cost guide SHALL explain that prior messages included in each follow-up are billed as input again, distinguish saved history from model context, and include a bounded conversation example alongside per-request estimates at the 512-token output cap, with explicit total-input and Lambda-duration assumptions. It SHALL identify localStorage as browser-only persistence with no added AWS storage service.

#### Scenario: Estimate follow-ups
- **WHEN** a user reviews a multi-turn workload estimate
- **THEN** the estimate counts resent user and assistant messages as input on each call rather than charging for the latest prompt alone
