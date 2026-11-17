# Design

## Context

See proposal.md for motivation. The `azure` branch currently contains a working React UI and Flask factory, with AWS-specific authentication, model calls, deployment, and examples. `frontend/src/data.ts` validates AWS URL shapes, `auth.ts` requests Cognito scopes and compares `sub`, and backend `OwnerAuth` expects Cognito claims. History keys include issuer and subject. CI runs exact coverage gates and Lambda packaging/smoke tests. Published main specs are absent. The earlier AWS change remains active with incomplete live checks, and the user reports AWS teardown complete.

The owner uses a personal Microsoft account. Read-only preflight verified an enabled FreeTrial subscription with spending protection enabled, subscription Owner access, and Global Administrator directory membership with application creation allowed. Subscription ownership and directory permissions remain separate checks. Credit balance/expiry, billing currency, budget support, actual app registration/consent, and deployment/inference readiness remain unverified.

## Goals / Non-Goals

**Goals**

- Establish an Azure inference path before spending on application hosting.
- Reuse Flask, React, OIDC, conversation contracts, and coverage gates.
- Publish secret-free application images publicly and keep model credentials keyless.
- Make each deployment stage and its costs reviewable in Terraform.

**Non-Goals**

- Provider switching at runtime, AWS/Azure state migration, custom models, agents, retrieval, or a database.
- Creating a Microsoft tenant automatically, changing subscription directories, administering the owner's personal password, or requiring a paid Entra license.
- Guaranteed sub-USD-5 spend, a hard spending cap, global distributed rate limiting, or immediate revocation of issued access tokens.

## Decisions

### 1. Use the subscription's Entra directory with a single owner

First document Azure CLI sign-in with the personal account, explicit subscription selection, tenant ID, and the user's object ID in that tenant. Verify directory membership, app-registration permission, API consent, Azure resource provisioning, role-assignment permission, provider registration, Cost Management access, and Container Apps regional quota separately. If the personal account cannot administer app registrations in that directory, report the exact missing permission and obtain tenant-administrator assistance before application deployment. A new tenant or subscription transfer is a separate decision.

Provision two single-tenant Entra app registrations and corresponding service principals through the AzureAD provider. The public SPA registration uses authorization code/S256 PKCE and an exact HTTPS root redirect and logout URI. The API registration exposes delegated `query` scope under `api://<api-client-id>/query` and requests v2 access tokens. Configure the consent/preauthorization relationship for this SPA. Browser discovery uses a tenant-specific authority, not `common` or `consumers`. The owner's personal account signs in as its member/guest identity in this tenant.

Retain `oidc-client-ts`, using discovery-provided token/logout endpoints and Entra logout parameters. Request `openid profile email` and the API scope. Email is optional display data, never an authorization identifier. Public runtime configuration contains tenant ID, SPA client ID, API audience/scope, owner object ID, and same-origin API base. Validate types, GUIDs, fixed Microsoft authority host, scope/audience consistency, and HTTPS origin explicitly.

The backend validates RS256/JWKS, signature, expiry/not-before, tenant-specific issuer, `ver=2.0`, exact API `aud`, `tid`, delegated `scp` containing `query`, `azp` matching the SPA, and `oid` matching the configured owner. Reject missing settings, ID tokens, app-only tokens, other tenants/users/clients, and malformed claims before inference. The browser checks the ID-token tenant/owner object ID for UI behavior, with backend authorization authoritative. Discovery supplies the JWKS URI rather than appending Cognito's JWKS path.

The API is exposed through Container Apps HTTPS ingress, with authorization enforced by Flask on every `/query` request. Static assets and readiness are public. Forwarded identity headers never authorize requests. No extra authentication proxy is introduced. This retains existing bearer-token semantics while removing dependence on API Gateway's JWT authorizer.

Alternatives considered include Entra External ID and Static Web Apps built-in authentication. They introduce additional tenant or hosting-specific behavior without helping a single owner who can use the subscription directory.

### 2. Bootstrap Azure OpenAI and prove inference before hosting

Use Azure OpenAI pay-per-token deployment, initially proposing `gpt-5-mini` version `2025-08-07` and SKU `GlobalStandard`. Select an available US resource region by verified total operating cost, including model, compute, and egress, with quota/capacity as eligibility constraints. East US 2 has no special preference. Global inference processing is acceptable because the owner prioritizes cost over US-only inference. These are planning defaults pending subscription verification. Preflight checks the current model lifecycle, availability to new deployments, regional capacity/quota, exact API support, minimum permitted deployment capacity, and prices. Record Global Standard's potential processing outside the resource region. Block deployment if eligibility fails. Model, version, region, or deployment type changes must be explicit and reflected in the cost guide and Terraform plan.

On 2026-11-13, the owner's East US 2 usage response reported unused Global Standard GPT-5 mini quota of 500 thousand tokens per minute (500,000 TPM), while GPT-5 nano Global Standard and US Data Zone quota were zero. The owner explicitly selected GPT-5 mini. This verifies reported quota only; it does not establish deployment capacity or successful inference. Recheck the selected mini model/version lifecycle and pricing before provisioning; do not reuse nano-specific availability or retirement evidence.

Use `infra/azure/model/` for the project resource group, Azure OpenAI account and deployment, scoped developer inference role, and resource-group budget. Disable local/key authentication and avoid producing resource keys. The signed-in developer receives `Cognitive Services OpenAI User` at this dedicated account scope. This built-in role is broader than model-specific IAM invocation, so document its scope and isolate this project's deployment in its own account. Runtime and deployment identities remain separate.

A small CLI/SDK script acquires an Entra token and sends a synthetic `Hello` through the same deployed model with a 32-token completion limit and bounded timeout. Report status, safe error code/request ID, and usage without displaying credentials. A reasoning-only/empty completion does not establish usable chat access. One deliberate, separately recorded follow-up at the normal 512-token cap can establish visible text, without automatic billable retries. Check budgets are supported by the subscription and active before this billable probe. A failed probe leaves the application hosting stage undeployed and documents cleanup for the model stage.

### 3. Preserve LangChain at the model boundary

Replace `langchain-aws` and AWS SDK imports with `langchain-openai` and `azure-identity`. Use `AzureChatOpenAI` with the confirmed endpoint, deployment name, compatible pinned API version, and an Entra bearer token provider. In the container use explicit managed-identity credentials. Local CLI/SDK examples use explicit Azure CLI credentials with the selected tenant, avoiding accidental credential fallback. Model configuration is server-side, required, and validated before readiness is declared healthy.

Keep `answer(prompt, history)` and injectable Flask services. Preserve human/assistant ordering, no client system/tool messages, and normalize usage to existing `input_tokens` and `output_tokens`. For GPT-5 mini use supported `verbosity=low`, `reasoning_effort=minimal`, and `max_completion_tokens=512`, counting reasoning tokens within that completion budget. Add a server-owned instruction to answer concisely by default, without accepting client-supplied system/developer instructions. Do not send unsupported temperature parameters or increase the cap automatically. Return a safe actionable error for empty completions/refusals or malformed usage. A capped response can end at the provider's limit, which the documentation must explain.

Bound connect/read timeouts and disable automatic retries initially. Map credential/access errors to 503, throttling to 429, timeout to 504, and unexpected provider/response failures to 502. Log only fixed diagnostic labels, bounded known error categories, status, request IDs, and timing. Never print provider exception strings or response/request bodies.

The alternative of direct OpenAI SDK calls would work, but retaining the existing LangChain message interface reduces migration scope.

### 4. One container serves Flask and the static frontend

Use `infra/azure/app/` for a user-assigned managed identity, a Consumption Container Apps environment, and one Container App. Read the model root's public output values through explicit validated inputs. Keep the two state files independent. Deploy public `ghcr.io/<owner>/<image>@sha256:<digest>` Linux/amd64 images. Azure pulls anonymously, with no registry credentials or AcrPull role. Grant the managed identity inference access at the project's Azure OpenAI account.

Publish to GitHub Container Registry through an explicit release step using a publisher credential held outside Terraform, the image, and the running app. Document package visibility configuration separately from repository visibility and verify anonymous pulling of the exact digest before Azure activation. Anyone can download image layers and inspect bundled application code/assets even when the repository is private. Use an allowlisted build context and exclude credentials, state/plans/backups, private configuration, logs, and conversation data from every image layer. Inject environment-specific configuration at runtime. Test image contents and inspect build history for secret exposure before publication. CI checks build locally and leave publication to the explicit release step.

Use one multistage image that builds Vite assets and installs locked production Python dependencies in a standard CPython 3.14 Linux image. Preserve the repository's patch-version and Pipenv conventions. Replace the AWS adapter, Lambda image, ZIP, and layer with Gunicorn bound to `0.0.0.0:8000`, stderr errors, access logs disabled, and control socket disabled. Run as a non-root user. Tests run with a read-only root filesystem and writable temporary directory.

Flask serves `/`, hashed static assets, `/config.json`, `/query`, and `/ready`. Restrict static paths to the build directory and avoid a catch-all that turns unknown API routes into HTML. Return no-cache HTML and no-store config, and immutable caching for hashed assets. Same-origin API calls remove the cross-origin dependency. Public config is generated from runtime settings and contains no secrets.

Container Apps initially uses 0.25 vCPU/0.5 GiB, minimum zero and maximum one replica, HTTPS-only external ingress, a readiness probe, and single active revision. Use one Gunicorn worker with enough threads for probes while one process-local semaphore bounds inference to one in-flight request. Preserve a process-local token bucket at one accepted query per second with burst two after authentication and validation, returning 429 before model invocation when exhausted. Scaling rules alone are not request throttles. Replica/revision replacement can briefly overlap, so these are per-process controls rather than an account-wide guarantee.

Deliver no-referrer, nosniff, frame denial, HSTS, and a CSP allowing bundled assets, same-origin requests, and exact tenant discovery/token endpoints. Keep all callback-bearing access logs disabled. Route inference diagnostics through sanitized stderr. Initially configure the environment logs destination as `none` and use live log streaming for diagnosis. Document that retained diagnostics require a separately priced and reviewed logging change.

Alternatives considered include Functions, which adds a WSGI/runtime compatibility change, and separate Static Web Apps hosting, which adds origin/configuration and potentially paid backend integration. Public GHCR removes the fixed Azure registry charge and pull-secret management. The owner accepts public image distribution. Recheck GitHub's current container storage/bandwidth pricing before releases and document publisher/Actions costs separately from Azure consumption.

### 5. Stage deployment without circular dependencies

The app root creates identity resources before the application resource is enabled. Use a narrowly documented `deploy_app` bootstrap input defaulting false until a publicly pullable image digest is available. This is a staging control for one application, not a provider abstraction.

1. Run read-only subscription, directory, permissions, quota, currency, and pricing checks. Obtain an active USD-billed subscription or an explicitly agreed local-currency budget equivalent.
2. Review/apply the model root, including budget and developer RBAC. Wait for RBAC propagation with bounded retries of authorization checks and perform the deliberate CLI inference probe.
3. Build/test the application locally, verify image-layer secret exclusion, then publish the tested public GHCR image with an explicit release command and verify an anonymous pull by digest. Review/apply the app bootstrap for runtime identity.
4. Review/apply `deploy_app=true` with the public image digest and owner configuration. Grant model access before container startup. Create initial Entra registrations with no redirect, create the app/FQDN, then populate exact redirect/logout URLs and public runtime identity config. Missing owner or identity configuration keeps `/query` closed during staging.
5. Test live owner sign-in and bounded inference plus unauthorized access, browser privacy, and persistence. Record measured cold-start/inference costs and any failed checks.

The owner is an existing directory identity. No temporary password, Cognito invitation, or email-to-subject bootstrap is carried over.

### 6. Replace active AWS behavior on this branch

Keep the `bedrock_chat` Python package path during the migration to avoid a mechanical rename of every import. Rename user-facing AWS labels and runtime configuration to Azure terms. Replace active `infra/bedrock/`, AWS IAM documents, Lambda packaging/tests, examples, and cost/setup instructions once equivalent Azure checks pass. Preserve AWS state/backups outside source control and never treat empty local state as proof that unrelated AWS resources are absent. Do not destroy AWS resources during this planning or Azure implementation workflow without a teardown request.

The existing AWS OpenSpec change remains unchanged with incomplete validation accurately represented. The two new Azure capability specs become the Azure branch's contract without claiming the original AWS work is complete.

Browser history stays isolated by provider/tenant and owner object ID. A new Azure origin will not automatically receive localStorage from the former CloudFront origin. Retain old messages at their old origin and document manual access/clearing. Do not auto-import AWS records or reuse a Cognito subject as an Entra object ID. Preserve versioned storage, retention defaults, navigator locks, generation guards, and cross-tab erasure.

Use AzureRM and AzureAD Terraform providers with pinned compatible constraints and committed platform locks. Runtime, deployment, directory, and GitHub publishing permissions have separate documented scopes. Local state/plans remain ignored. Saved plans are single-use operational artifacts and must be regenerated after partial applies or changing inputs. Teardown order is app deployment/identity followed by model resources/budget. Cross-root RBAC is owned in the app root and removed before model destruction. Terraform teardown does not delete published GHCR packages. Document explicit package/version cleanup, retain the previous deployment digest for rollback, and delete published versions only when requested.

### 7. Cost and validation

Owner-approved acceptance scope revision: task 6.2 requires the complete browser checklist, representative live authentication rejection checks using available credentials, and full offline adversarial token-claim tests. The isolated live matrix requiring unavailable tokens or additional identities/app registrations is not a completion gate. Record those cases as unverified rather than passed. All runtime authentication requirements remain unchanged.

The resource-group budget covers both roots' Azure resources, including OpenAI, Container Apps, egress, and any enabled monitoring. GitHub registry and publisher/Actions usage fall outside this Azure budget and must be reported separately. Default to USD 5 only for USD billing. Cost Management uses billing currency, so another currency requires a documented converted amount rather than labeling five local units as five USD. Configure monthly actual-cost emails at 50%, 80%, and 100%. Costs/alerts can lag, credits differ by offer, and budgets do not stop consumption.

Create dated sourced gross and net estimates for 100, 1,000, and 10,000 requests with declared input/history sizes and 512 completion tokens. Include reasoning output billing, repeated history input, cold starts, scale-to-zero billing/free grants, public GHCR pricing assumptions, egress, and exclusions. GitHub currently offers free container image storage and bandwidth, but verify that policy and separate any build/Actions charges. Assume zero promotional credits and distinguish verified recurring free grants from credit assumptions. Check whether subscription Cost Management reports include all model charges and show the baseline cost relative to the budget before applying the app stage.

Retain exact 100% Python statement/branch and frontend statement/branch/function/line gates, including unimported source. Update provider/auth/error fixtures and existing tests. Add targeted regression checks for tenant/audience/owner/client validation, safe diagnostics, empty reasoning completions, same-origin static delivery/security headers, and rejected requests making no inference calls. Replace Lambda emulator checks with Docker HTTP checks and mocked Azure Terraform tests. CI remains credential-free and performs builds/checks without cloud deployment or package publication.

## Risks / Trade-offs

- Personal-account directory permissions may be insufficient. Verify identity/app-registration capability before creating hosting and report specific administrator assistance required.
- Model availability, capacity, version retirement, and Global Standard geography change. Recheck authoritative Microsoft documentation and subscription responses before a reviewed apply.
- GPT-5 reasoning can consume a small completion cap. Test visible output at 512 tokens and keep empty responses as explicit failures rather than silently raising cost limits.
- Public images expose application code and all image layers. Exclude secrets and private files at build time, verify anonymous digest pulls, and treat public image publication as independently visible from a private source repository.
- GitHub pricing or image availability may change. Recheck registry terms, retain deployed/rollback digests, and report external costs outside the Azure budget.
- Scale-to-zero introduces cold starts. Measure browser timeouts and readiness with the deployed CPU/memory before recording acceptance.
- An unprotected static shell and ingress remain reachable. Enforce owner tokens before model access and test direct `/query` calls without relying on CORS or UI checks.
- Cross-tenant token handling and stale browser records can expose another owner's data. Require exact tenant/object IDs and isolate persistence namespaces.

## Migration Plan

Implement and validate offline changes first, then follow the stages above with fresh saved plans. Preserve the last working image digest for application rollback within Azure. Infrastructure or identity rollback requires a reviewed plan, and image rollback does not restore old claims/configuration automatically. The AWS branch and original change provide source history only, since the user destroyed its deployment and AWS inference remains unverified. Teardown is an explicit operation and retains Terraform state/backups until resource removal is confirmed.

## Open Questions

- Actual subscription ID, tenant ID, owner object ID, names, email, billing currency, and registry naming are deployment inputs.
- Candidate model/version/region capacity, deployment minimum, and actual price must be confirmed by the prescribed preflight. Failure pauses cloud deployment at that stage.

## References

Reviewed November 13, 2026. Subscription-specific access and prices are unverified.

- [Subscription and tenant relationship](https://learn.microsoft.com/en-us/entra/fundamentals/faq)
- [Entra app registration](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app)
- [Access-token validation](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens)
- [Tenant and object claims](https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation)
- [Azure OpenAI model availability](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability)
- [Reasoning parameters and token limits](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning)
- [Model retirement schedule](https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule)
- [Keyless model access](https://learn.microsoft.com/en-us/azure/developer/ai/keyless-connections)
- [Container Apps managed identity](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity)
- [Container Apps scaling](https://learn.microsoft.com/en-us/azure/container-apps/scale-app)
- [Container Apps billing](https://learn.microsoft.com/en-us/azure/container-apps/billing)
- [Container Apps log destinations](https://learn.microsoft.com/en-us/azure/container-apps/log-options)
- [Resource-group budgets](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets)
- [Azure OpenAI pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/)
- [GitHub Container Registry visibility and authentication](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [GitHub Packages and container-registry billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages)

## Owner-approved AWS artifact cleanup (November 17, 2026)

The owner subsequently requested removal of the historical AWS OpenSpec change,
obsolete AWS saved plans/provider cache and Lambda cache. This supersedes the
earlier requirement to retain AWS planning artifacts. Private AWS state/backups
remain Git-ignored in `infra/retained-aws-state/`. Active `bedrock_chat` imports,
package names, OIDC prefix and protective AWS regression/image checks remain.
No cloud resources were changed by local cleanup.
