# Spec Delta

## Purpose

Provide owner-authenticated model-only conversations on Azure through browser and direct CLI/SDK access, preserving the existing conversation and privacy behavior during the provider migration.

## ADDED Requirements

### Requirement: Azure identity readiness
The deployment workflow SHALL verify the selected subscription, associated Entra tenant, owner's directory object ID, and separate resource, role-assignment, and app-registration permissions. It SHALL support a personal Microsoft account represented in that tenant and report missing prerequisites before deploying application hosting.

#### Scenario: Personal account can use the directory
- **WHEN** the owner signs into a supported subscription and has the required tenant permissions
- **THEN** the workflow identifies the tenant and immutable owner object ID for single-tenant application sign-in

#### Scenario: Directory permissions are missing
- **WHEN** subscription access exists but application registration or consent is denied
- **THEN** deployment reports the missing directory permission and administrator action before hosting is deployed

### Requirement: Staged model access verification
The workflow SHALL verify model lifecycle, deployment availability, region, API support, capacity, and account eligibility before deployment. It SHALL permit a separately reviewed minimal model deployment and bounded CLI probe before application hosting. A failed probe SHALL block the hosting stage without silent model or region fallback.

#### Scenario: Model access is rejected
- **WHEN** a minimal model request fails because of subscription restrictions, permission, quota, or model availability
- **THEN** diagnostics identify the failed stage and safe provider code while the chat hosting stage remains undeployed

#### Scenario: Model access is established
- **WHEN** a bounded request returns usable text and token usage through the chosen deployment
- **THEN** the workflow records its model, version, region, deployment type, and successful result before proceeding

### Requirement: Reproducible Azure provisioning
Terraform SHALL provision reviewable Azure model and application resources with separate state and keyless runtime inference. Runtime inference permissions SHALL be scoped to the project's model account. Container images SHALL use anonymous public GHCR pulls pinned by digest. Outputs SHALL identify the endpoint, deployment, tenant, client identifiers, and application URL without credentials.

#### Scenario: Runtime identity
- **WHEN** the application invokes the model
- **THEN** its managed identity has inference access at the dedicated model-account scope without subscription-management permissions or model API keys

#### Scenario: Reviewable stages
- **WHEN** a user reviews model bootstrap, application bootstrap, or application activation plans
- **THEN** each plan identifies only that stage's intended resources and preserves previously managed state

### Requirement: Public application image distribution
The release workflow SHALL publish application images to public GitHub Container Registry and verify anonymous pulling of the deployment digest. Images SHALL exclude credentials, Terraform state/plans, private configuration, logs, and conversation data from all layers. Documentation SHALL explain that image contents are publicly inspectable independently of repository visibility.

#### Scenario: Image publication
- **WHEN** a tested image is released
- **THEN** its exact digest is anonymously pullable and image-layer checks confirm that only intended application artifacts and dependencies are included

#### Scenario: Private source repository
- **WHEN** an image is published from a private repository
- **THEN** the release documentation identifies the image as public and runtime owner authentication still protects model queries

#### Scenario: Azure teardown
- **WHEN** Terraform-managed Azure resources are destroyed
- **THEN** published GHCR versions remain available until separately requested package cleanup and the documented rollback digest is identified

### Requirement: Owner-only Entra browser access
The browser SHALL use tenant-specific authorization-code sign-in with PKCE and in-memory tokens. The API SHALL validate signature, issuer, lifetime, tenant, API audience, delegated query scope, authorized browser client, and immutable owner object ID before inference. Missing owner settings SHALL deny all queries.

#### Scenario: Authorized owner
- **WHEN** the configured owner authenticates through the configured SPA client and sends a valid API access token
- **THEN** the API accepts a valid query and returns model text and usage

#### Scenario: Invalid identity or token
- **WHEN** a request has no token, an ID token, an expired or invalid token, missing query scope, or another tenant, audience, client, or owner
- **THEN** the API denies the request without invoking the model, including when forged identity headers are supplied

#### Scenario: Unconfigured application
- **WHEN** initial deployment lacks required owner or authentication settings
- **THEN** the public shell can display safe configuration feedback and every model query is denied

### Requirement: Bounded conversational API
POST `/query` SHALL preserve the JSON prompt/history contract, 4,000-code-point prompt limit, ten completed history pairs, 32,000 combined code points, and 256 KiB request limit. The server SHALL enforce a maximum 512 completion tokens, including provider reasoning where applicable. It SHALL return complete non-streamed text and normalized input/output usage.

#### Scenario: Valid follow-up
- **WHEN** the owner submits a valid prompt with completed conversation pairs
- **THEN** retained human/assistant messages accompany the prompt in order and one model invocation returns text and nonnegative integer usage

#### Scenario: Malformed or excessive input
- **WHEN** input violates shape, role, Unicode, size, pair count, or client-controlled generation rules
- **THEN** the API rejects it before inference

#### Scenario: Reasoning exhausts the completion budget
- **WHEN** the provider returns no usable text within the configured cap
- **THEN** the application shows a safe failure without a fabricated answer, an automatic retry, or an automatic token-budget increase

### Requirement: Concise answer defaults
The application SHALL request low verbosity and minimal reasoning effort for the selected GPT-5 mini deployment, with a server-owned instruction to answer concisely and a 512-token completion cap. Client input SHALL NOT override these defaults or introduce system/developer instructions.

#### Scenario: Short answer request
- **WHEN** an authorized user submits a valid question
- **THEN** the model request applies the concise-answer instruction, low verbosity, minimal reasoning, and the fixed completion cap

### Requirement: Safe inference failures and diagnostics
The API SHALL return safe errors for authentication/access, quota, timeout, and provider failures. Operational diagnostics SHALL include only sanitized error categories, status, request identifiers, and timing. Credentials, prompts, answers, authorization headers, callback values, and raw provider exception text SHALL be excluded.

#### Scenario: Provider validation failure
- **WHEN** the model rejects a request
- **THEN** the browser receives a safe error and operational diagnostics identify a safe provider category and available request ID without request content

### Requirement: Bounded application execution
Application compute SHALL scale to zero and have a maximum one replica in normal steady-state operation. Per application process, inference SHALL allow at most one in-flight request and one accepted query per second with burst two. Excess authorized requests SHALL receive 429 before inference. These controls SHALL be documented as throughput limits with revision/restart limitations.

#### Scenario: Overlapping requests
- **WHEN** a second authorized model request arrives while inference is active or the rate allowance is exhausted
- **THEN** it is rejected without an additional model invocation

### Requirement: HTTPS shell and static asset boundaries
The application SHALL serve browser assets, public runtime configuration, readiness, and the protected query API over a generated HTTPS origin. Configuration SHALL contain no credentials. Unknown API routes and unsafe static paths SHALL be rejected. HTML SHALL revalidate, runtime configuration SHALL be non-cacheable, and hashed assets SHALL support immutable caching.

#### Scenario: Anonymous visitor
- **WHEN** an unauthenticated visitor loads the public shell or config
- **THEN** only public application/identity settings are available and model queries still require owner authorization

#### Scenario: Static path traversal
- **WHEN** a path attempts to escape the built frontend assets
- **THEN** no file outside the asset directory is served

### Requirement: Existing browser conversation behavior
The frontend SHALL preserve You/Assistant messages, a scrollable transcript, loading/error/usage feedback, multiline Submit, Enter submission, Shift+Enter newline, IME safety, copy-answer feedback, and Clear conversation/Sign out. It SHALL send newest-ten-pair bounded context while retaining older saved messages independently.

#### Scenario: Submission and copy
- **WHEN** a valid draft is submitted by click or Enter
- **THEN** exactly one request starts and submission is guarded until completion, while copying a completed answer sends no model request

#### Scenario: Composition and reading history
- **WHEN** the owner composes text with an input method, inserts a newline, or reads older messages
- **THEN** composition does not send a request and scroll behavior preserves reading position

### Requirement: Owner-isolated browser persistence
The frontend SHALL retain versioned local history keyed by Azure tenant and owner identity, bounded to the newest 100 completed exchanges and 1 MiB UTF-8 JSON. Restore SHALL occur only after owner authentication. Clear/logout and cross-tab invalidation SHALL prevent late responses from recreating erased history. Storage failures SHALL be visible and allow in-memory use.

#### Scenario: Refresh and reopen
- **WHEN** the same Azure owner signs in after refresh or reopening
- **THEN** valid retained messages restore in order with retention and context notices

#### Scenario: Clear during inference
- **WHEN** the owner clears or logs out while a request or another tab is active
- **THEN** saved messages are removed and stale responses/tabs cannot recreate them

#### Scenario: AWS-origin history
- **WHEN** the Azure site first loads after migration
- **THEN** AWS-origin localStorage is not imported or assigned to an Azure owner, and documentation explains the origin boundary and manual clearing

### Requirement: Callback and browser privacy
The browser SHALL validate OAuth state/PKCE, replace the callback URL with the clean root URL on success or failure, and remove transient auth state. The application SHALL enforce CSP, no-referrer, nosniff, frame denial, and HTTPS. Tokens SHALL remain outside persistent storage. Enabled access logs SHALL exclude callback/query secrets, cookies, and authorization values.

#### Scenario: Callback rejection
- **WHEN** an OAuth callback is malformed, rejected, or fails token exchange
- **THEN** authentication fails safely and URL/history/logs contain no raw callback values

#### Scenario: Inert content and delivered headers
- **WHEN** Chrome loads saved HTML-like content and completes sign-in/query/logout
- **THEN** text remains inert, the enforced security headers allow required behavior, and unauthorized scripts or connections are blocked

### Requirement: Model-only answers
The application SHALL use the selected Azure model and supplied conversation context without retrieval, browsing, external tools, or model fallback. The UI SHALL explain that answers are not verified against live sources.

#### Scenario: Time-sensitive question
- **WHEN** a user requests current information
- **THEN** the application performs no external search and makes no live-source verification claim

### Requirement: Azure CLI and SDK examples
The project SHALL provide direct Azure CLI token/HTTP and Python SDK examples with temporary Entra credentials, the same verified endpoint/deployment, a default 512 completion-token limit, usage reporting, and bounded timeouts. Failures SHALL exit unsuccessfully with safe actionable diagnostics and no automatic fallback.

#### Scenario: Direct invocation
- **WHEN** an authorized developer runs either example
- **THEN** it returns text and input/output usage without model API keys

### Requirement: Migration validation and lifecycle
The Azure branch SHALL replace active AWS deployment paths and instructions while preserving private state/backups. The original AWS OpenSpec change may be removed under the owner-approved November 17, 2026 cleanup scope. Offline CI SHALL enforce exact 100% application coverage and Azure configuration/container checks without cloud credentials. Live deployment and browser acceptance SHALL be recorded independently of offline success.

#### Scenario: Offline coverage gate
- **WHEN** source has any uncovered Python statement/branch or frontend statement/branch/function/line, including unimported source
- **THEN** checks fail without making live model calls

#### Scenario: Teardown and rollback
- **WHEN** the user requests Azure cleanup or application rollback
- **THEN** reviewed plans/image digests identify the affected resources, app resources are removed before model resources, and state is retained until teardown is verified
