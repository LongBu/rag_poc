# Proposal

## Why

The AWS application reached deployment but Bedrock rejected even a minimal CLI invocation with an account-level restriction. Replace the AWS deployment on the `azure` branch with an Azure implementation that verifies model access early and preserves the existing owner-only chat experience and USD 5 monthly alert budget.

## What Changes

- **BREAKING** Replace AWS infrastructure, credentials, model invocation, and Cognito sign-in with Azure Terraform, Azure OpenAI inference, managed identity, and Microsoft Entra sign-in.
- Add a staged model-access bootstrap and bounded CLI/SDK test before deploying application hosting. Check subscription eligibility, model lifecycle, regional deployment capacity, and permissions explicitly.
- Propose GPT-5 mini through a pay-per-token Global Standard deployment, selecting an available US resource region by verified total operating cost rather than fixing East US 2. Global inference processing is acceptable. Record model/version, deployment type, region, quota, and price evidence before provisioning.
- Serve Flask and the built React frontend together in one scale-to-zero Azure Container App, preserving HTTPS, owner authorization, security headers, and browser privacy.
- Publish secret-free application images to public GitHub Container Registry and deploy immutable digests through anonymous pulls. The image's application code/assets are publicly downloadable, while source repository visibility remains independently controlled.
- Support the owner's personal Microsoft account through its representation in the subscription's Entra directory. Verify tenant membership and app-registration permissions before relying on this path.
- Use low verbosity, minimal reasoning effort, and a 512-token completion cap for concise answers. Preserve prompt/history limits, complete non-streamed responses, usage reporting, follow-ups, copy/keyboard behavior, bounded local history, and clear/logout safeguards.
- Provision an Azure resource-group monthly cost budget defaulting to USD 5, with actual-cost email alerts at 50%, 80%, and 100%. Explain currency, delays, exclusions, and the absence of a spending cap.
- Replace AWS deployment documentation, examples, packaging, and CI checks with Azure equivalents while retaining exact application coverage gates.

## Capabilities

### New Capabilities

- `azure-chat-access`: Azure model access, owner identity, browser/CLI/SDK behavior, deployment lifecycle, and retained conversation safeguards.
- `azure-chat-cost-controls`: Subscription preflight, staged cost exposure, sourced estimates, and scoped budget notifications.

### Modified Capabilities

None. `openspec/specs/` has no published capabilities. The AWS requirements live in the separate active `add-budget-bedrock-access` change, which remains an historical planning reference with incomplete live checks preserved.

## Impact

Implementation affects `backend/src/bedrock_chat/`, backend dependencies/tests/examples, container packaging, `frontend/src/auth.ts`, `data.ts`, history identity keys, associated frontend tests, Terraform, CI, README, and cost/permissions documentation. Add `infra/azure/` with isolated state and staged model/app roots. Replace active AWS paths and dependencies on this branch after Azure validation, preserving any local AWS state/backups and the original OpenSpec change. External dependencies include Azure Resource Manager, Entra application registrations, Azure OpenAI, Container Apps, Cost Management, and public GitHub Container Registry. Image publication requires GitHub publishing access and an explicit release step. GitHub costs are tracked separately from the Azure budget. Custom models, retrieval, agents/tools, server-side chat storage, public registration, and parallel AWS/Azure runtime support are excluded.

## Owner-approved AWS artifact cleanup (November 17, 2026)

The owner subsequently requested removal of the historical AWS OpenSpec change,
obsolete AWS saved plans/provider cache and Lambda cache. This supersedes the
earlier requirement to retain AWS planning artifacts. Private AWS state/backups
remain Git-ignored in `infra/retained-aws-state/`. Active `bedrock_chat` imports,
package names, OIDC prefix and protective AWS regression/image checks remain.
No cloud resources were changed by local cleanup.
