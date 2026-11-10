# Proposal

## Why

Provide inexpensive model-only general-question conversations through the user's AWS account with predictable cost estimates before any deployment. Bedrock's managed on-demand inference avoids hosting infrastructure and allows private browser, CLI, and SDK use without relying on unknown Free Tier credits.

## What Changes

- Add Terraform configuration for a dedicated assumable Bedrock invocation role and a monthly cost budget with email alerts.
- Default to Amazon Nova Micro, standard on-demand inference in `us-east-1`, subject to account availability checks before deployment.
- Use a 512-token output limit for browser answers and CLI/SDK examples, with reported token usage.
- Answer general questions from the model and supplied conversation context only, without web search, retrieval, or external tools.
- Document token pricing, example workloads, credit verification, authentication, plan/apply, troubleshooting, and teardown.
- Use the accepted configurable USD 5 monthly alert budget across the application services; clarify that alerts do not cap spending.
- Add a Chrome-compatible React/TypeScript/Vite static frontend on private S3 through CloudFront, an API Gateway HTTP API, and a Flask-based Python Lambda using AWS Lambda Web Adapter and LangChain ChatBedrockConverse.
- Provide a simple scrollable chat layout with You/Assistant labels, Copy answer on each assistant message, a multiline composer with Submit, and Clear conversation/Sign out controls. Enter submits; Shift+Enter inserts a newline.
- Support conversational follow-ups with up to 10 recent completed exchanges plus the current prompt, bounded total input, and complete responses with a loading indicator.
- Persist owner-specific conversation messages in Chrome localStorage across refresh/reopening; restore only after authentication, clear on explicit logout or Clear conversation, and keep authentication tokens out of persistent storage.
- Require pytest unit tests with 100% Python statement/branch coverage and Jest tests with 100% frontend statement/branch/function/line coverage, enforced locally and in CI.
- Restrict application use to the owner with Cognito Lite password sign-in, disabled public sign-up, JWT validation, and a backend user-subject allowlist.

## Capabilities

### New Capabilities

- `bedrock-access`: Terraform-managed least-privilege access to one managed text model through CLI, SDK, and an owner-authenticated browser application.
- `bedrock-cost-controls`: Upfront cost estimates, configurable budget notifications, and explicit credit and spending limitations.

### Modified Capabilities

None. The repository contains no existing capability specifications.

## Impact

This is a greenfield repository containing OpenSpec configuration only. Implementation will introduce `infra/bedrock/`, a Flask Python Lambda, a React/TypeScript/Vite frontend, local invocation examples, dependency declarations, tests, and documentation. AWS dependencies include IAM, Bedrock Runtime, STS, Budgets, Lambda, API Gateway HTTP APIs, Cognito Lite, S3, CloudFront, and CloudWatch Logs. Flask, a production WSGI server, Lambda Web Adapter, and LangChain run in Lambda; React/TypeScript/Vite, Jest, React Testing Library, pytest, and pytest-cov add build/test dependencies; the browser contains no AWS secrets. Dedicated model deployment, training, provisioned throughput, server-side chat-history storage, custom domains, and public user registration are excluded. Planning makes no account changes and does not establish credit eligibility.
