# Design

## Context

The repository contains OpenSpec planning only; there is no existing application or Terraform to migrate. The confirmed purpose is inexpensive model-only general-question conversations in Chrome, with CLI/SDK access, Flask/LangChain on Lambda, React/TypeScript/Vite, owner-only sign-in, complete responses, localStorage persistence, and a USD 5 monthly alert budget. Account credentials and credits have not been inspected. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:** Reviewable Terraform-managed serverless infrastructure, bounded conversational inference, temporary credentials, owner-specific browser persistence, explicit cost assumptions, and exact 100% application unit-test coverage.

**Non-Goals:** Training, provisioned model throughput, always-running servers, web search/retrieval/tools, cross-region inference, server-side conversation storage, custom domains, public registration, automatic credit discovery, and guaranteed monthly spending caps.

## Decisions

### Python runtime

Use standard CPython 3.14 consistently for local development, CI, Lambda
(`python3.14` on Amazon Linux 2023), and Python SDK examples. Use pyenv for the
local interpreter and pin its patch version in `backend/.python-version`. Build Lambda
dependencies for Linux and its configured architecture; validate pinned
dependencies and adapter packaging on Python 3.14 before deployment.

### Backend layout and dependencies

Keep backend source, tests, Lambda packaging, examples, and scripts under
`backend/`, alongside the pytest/coverage `pyproject.toml` and dependency
`Pipfile`/`Pipfile.lock`. Pipenv owns dependency declarations and the hashed lock;
CI verifies and syncs the lock rather than resolving dependencies. Build Lambda
from the backend Docker context, exporting only production dependencies with
hashes inside the container. Generated ZIPs live in `backend/artifacts/`;
Terraform references that path. Keep frontend and infrastructure as sibling
directories. No requirements files are maintained.

### Model and application API

Use regional `amazon.nova-micro-v1:0` in `us-east-1` through LangChain `ChatBedrockConverse`. Check model lifecycle, account access, direct on-demand availability, and current pricing before deployment. Do not silently change models or regions. The browser explains that model-only answers are not verified against live sources; the application does not supply fabricated live citations.

Flask exposes POST `/query` through an application factory with injectable authentication and model services. Accept JSON `prompt` and optional `history`, an array of completed `{user, assistant}` string pairs. Validate nonempty text, role/shape, at most 4,000 Unicode code points for the current prompt, at most 10 history pairs, 32,000 combined input code points, and a 256 KiB UTF-8 body. Map validated pairs to human/AI messages, never client system/tool messages. Reject oversized or malformed requests before inference. One accepted request makes one model call, with a server-enforced 512-token output maximum that clients cannot override. Return complete JSON text and token usage without streaming. Map credential/access/quota/provider/timeout errors safely without stack traces or secrets.

### Hosting and identity

Use private S3 with public access blocked and a CloudFront REST origin protected by Origin Access Control. Serve static assets over HTTPS using the generated distribution domain, avoiding DNS/domain costs. The shell and public OAuth settings are downloadable; private messages and queries require sign-in. A static frontend avoids Lambda rendering costs. Lambda functions have no public Function URL.

Use a dedicated Cognito Lite user pool with classic hosted login, self-registration disabled, no external providers, and a public client without a secret. Enable only authorization-code flow with S256 PKCE, random state, exact frontend callback/logout URLs, and the resource-server scope `chat/query`. Password sign-in is the initial scope; authenticator-app MFA is optional later without SMS. Use a maintained pinned browser OIDC client with in-memory tokens and only transient PKCE/state in sessionStorage. Callback processing removes transient state. Explicit logout clears local session and calls hosted logout; issued access tokens can remain valid until their short expiry.

Protect POST `/query` using the HTTP API JWT authorizer with exact issuer, app-client audience, and required scope. Flask independently validates bearer signatures using cached Cognito JWKS, issuer, client ID, expiry, access-token type, scope, and immutable owner `sub`. Never trust forwarded client identity headers. Missing owner configuration denies all queries. Scope Lambda invocation permission to the intended API route; allow CORS only from the frontend origin with required methods/headers. CORS is not authentication; preflight does not invoke Bedrock.

Create the sole owner through a documented administrator CLI bootstrap after the pool is deployed. Complete first-password setup through Cognito without putting passwords in Terraform variables/state, code, outputs, or logs. Retrieve the immutable subject and configure it through Terraform in a second apply; the initial empty value fails closed.

### Callback privacy and browser security

Process callbacks with the OIDC client, validating state and PKCE before accepting authentication. After capturing the parameters required by the client, replace the current browser-history entry with the clean root URL rather than adding a history entry. Remove authorization codes, state, and OAuth error parameters on both success and failure; clear transient authentication state and show only sanitized errors. Never log the callback URL or parameters.

Serve the frontend with `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, and an enforced Content Security Policy delivered by CloudFront response headers. Restrict executable scripts to bundled same-origin assets without unsafe inline scripts or eval; restrict connections to the required API and Cognito endpoints, block objects and framing, and restrict base URLs. Do not add analytics or third-party scripts. Verify the production build and actual Cognito flow work under the policy.

For any enabled CloudFront/API/origin access logging, use an explicit safe field allowlist: request ID, path without query parameters, status, and timing as applicable. Exclude query strings, cookies, Authorization headers, and referrers containing callback data. Use configurable log fields that satisfy these exclusions; do not enable a logging format that unavoidably captures callback secrets. Browser URL cleanup cannot remove data already recorded by infrastructure on the initial callback request.

Saved conversations remain in localStorage across browser restarts. Owner-specific keys prevent accidental cross-owner restoration but do not encrypt messages or protect them from same-origin JavaScript or someone with access to the unlocked browser profile. Explain this limitation in the persistence notice and documentation. Render prompts and answers as text, including HTML-like model output, without injecting HTML. CSP reduces injection exposure but does not make compromised application code trustworthy. Preserve in-memory tokens and the existing Clear conversation/logout erasure behavior.

Test successful, rejected, and failed callbacks for clean history, cleared transient state, and sanitized errors/logs. Test HTML-like prompts/answers remain inert text, no tokens enter localStorage, and clear/logout removes saved history. Assert response-header and access-log field configuration in infrastructure tests; verify delivered headers, CSP enforcement, referrer suppression, callback cleanup including Back navigation, and usable login in Chrome with synthetic callback markers that never appear in enabled access logs.

### Terraform and Lambda packaging

Use one root module in `infra/bedrock/` with pinned compatible provider/version constraints, lock file, variables, outputs, and sanitized example variables. Use the AWS credential chain/SSO. Supply the stable trusted principal ARN and budget email through `TF_VAR_trusted_principal_arn` and `TF_VAR_budget_email`, with Terraform sensitive redaction; do not save actual values in tfvars. Environment inputs still persist in Terraform plans/state and AWS configuration; protect those artifacts. Derive partition/account through data sources and review target identity before apply. Outputs include CLI role ARN, model/region, frontend/API URLs, and Cognito identifiers.

Maintain separate least-privilege roles: an assumable CLI role trusting only the configured principal, and a Lambda role trusted by Lambda. Grant `bedrock:InvokeModel` only on the configured regional foundation-model ARN; scope log writes to a precreated log group. Document the caller's independent `sts:AssumeRole` permission. Do not create long-lived keys or grant runtime billing/Marketplace permissions.

Package Flask with Gunicorn, pinned LangChain/JWT dependencies, and a pinned Lambda Web Adapter layer using its documented ZIP wrapper/bootstrap. Verify Linux/runtime/architecture compatibility, layer version/license, and ZIP/uncompressed limits. Use a private S3 deployment-artifact bucket only if direct ZIP upload size requires it; document lifecycle and teardown. No registry is required. Debug/development server is disabled. A local readiness endpoint never calls the model and is not exposed as an API route. Adapter smoke checks cover HTTP API request conversion, headers, bodies, status, errors, and readiness.

Run Lambda outside a VPC to avoid NAT costs, initially at 512 MB with reserved concurrency 1 and a 25-second timeout. Bound SDK timeouts/retries within that limit. HTTP API route throttling starts at 1 request/second, burst 2. These controls do not enforce a monthly cap. Retain logs seven days, recording only request IDs/status/latency/token counts, never prompts, answers, tokens, or Authorization headers. Keep local Terraform state initially; securely retain/backup it and ignore state, saved plans, private variables, credentials, build output, and `.terraform/`, while tracking dependency lock files. State can contain account identifiers/email. Add remote state later if collaboration requires it.

### Simple chat interaction

Use a single-column layout with Clear conversation and Sign out in the header, a scrollable transcript with explicit You/Assistant labels, and a multiline composer with Submit. Each assistant answer has Copy answer; display token usage, context/retention notices, errors, and loading feedback. Use plain-text rendering and accessible status labels.

Submit and Enter use one guarded submission path. Reject empty/oversized drafts and disable submission while pending. Shift+Enter inserts a newline; IME composition must never submit. Preserve a failed draft for deliberate retry. Scroll for new answers when near the bottom, preserving position when reading earlier messages.

Copy only the selected answer text through a user-initiated clipboard write, announce success only after resolution, and show a manual-selection suggestion when unavailable or rejected. Copying makes no model request. Test keyboard, composition, duplicate guards, copy success/failure, accessibility, and scroll intent under the 100% frontend coverage gate and verify real interactions in Chrome.

### React/TypeScript/Vite and testing compatibility

Use strict TypeScript `.ts` services/`.tsx` components and pinned React/Vite/npm dependencies in `frontend/`; build to `dist/` for S3. Use a root callback rather than requiring server-side routing. A tested runtime JSON loader reads public API/Cognito settings without secrets or Vite-only globals. Types cover messages, exchanges, API/usage, auth state, settings, and stored-record versions; validate external JSON at runtime too. `npm run typecheck` runs `tsc --noEmit` separately from Jest transpilation.

Use Jest with jsdom, Babel React/TypeScript transforms, pinned compatible packages, static-import mocks, and React Testing Library/user-event. Generate original TS/TSX source-map coverage and include entry points, auth, config, API, storage, context, clipboard, and keyboard logic. Browser boundary mocks do not replace testing component behavior. Keep real Chrome smoke checks for Cognito navigation, clipboard, keyboard, and refresh/reopen behavior.

### Conversation and local persistence

An exchange is one completed user prompt/assistant answer pair. Select the newest 10 completed exchanges plus the new prompt, dropping oldest whole pairs until combined input fits. Use identical Unicode-code-point counting on both sides. Saved history is independent of model context: display a notice when older visible messages are excluded, rather than deleting them merely for leaving context. Character limits are not exact token budgets. Failed requests never create fabricated pairs or trigger automatic billable replay; keep drafts for deliberate retry.

Store versioned completed pairs with timestamps keyed by pool issuer and owner subject in localStorage. Restore only after authentication/owner verification; tokens remain in memory, PKCE/state transient in sessionStorage. Refresh may redirect through Cognito. Browser reopening preserves messages, not a guarantee of an unexpired login or cross-device synchronization. No server database is created.

Document implementation defaults of the newest 100 completed exchanges and at most 1 MiB serialized UTF-8 JSON, removing oldest whole pairs when needed and showing a retention notice distinct from model-context notices. Validate schema/version/types/sizes; ignore corrupt/unsupported records safely. Handle unavailable storage, quota errors, and removal failures visibly and continue in memory rather than claiming persistence succeeded. Explain Chrome site-data deletion and same-origin JavaScript visibility.

Clear conversation erases visible/saved history while keeping login; explicit logout also clears drafts/tokens/transient auth before redirecting. A request-generation guard discards responses arriving after clear/logout. Handle owner-key removal events across tabs so stale tabs do not recreate erased records. Do not send prompts/tokens between tabs. If removal fails, explain Chrome site-data clearing. Test restore/owner isolation, corrupt/oversized data, quota failures, late responses, cross-tab deletion, context limits, and retention bounds.

### Enforced unit coverage and CI

Use pytest with pytest-cov/coverage.py across all first-party backend source, including unimported modules, with statement and branch measurement and exact 100% thresholds. Include routes/auth/JWKS/config/model/errors/readiness and any custom Python bootstrap. Use Flask's test client, dependency injection, fake clocks, and mocked AWS/JWKS; cover signatures/claims/key rotation, missing owner, validation/Unicode boundaries, provider failures, and secret-free logs offline. Generate terminal, XML, and JSON reports and verify exact uncovered counters to prevent rounding loopholes.

Jest collectCoverageFrom includes every first-party executable TS/TSX/JS module, imported or not. Require 100% statements, branches, functions, and lines globally and per file, with text/LCOV/JSON reports and exact counter checks. Exclude only dependencies, generated files, declarations, tests, and non-application tooling/configuration; no coverage-ignore directives or threshold reductions for application logic.

Document canonical backend `pytest --cov=src --cov-branch --cov-fail-under=100` and frontend `npm run test:coverage -- --runInBand` commands with correct source roots. CI performs clean pinned installs, both coverage gates, type checking, Vite build, and Terraform format/validation/tests. Provide a reviewable GitHub Actions workflow if no platform is established; do not publish a repository or activate external services. Keep adapter/Chrome/live AWS checks separate from offline coverage claims.

### Costs and alerts

Reference rates reviewed 2026-11-09 are USD 0.035 per million input and USD 0.14 per million output Nova Micro tokens. Live regional pricing tables were not exposed numerically during planning; confirm current us-east-1 standard on-demand prices through AWS pricing/Price List before deployment. Formula: `input_tokens / 1_000_000 * 0.035 + output_tokens / 1_000_000 * 0.14`.

| Queries/month | Total input/query | Output/query | Inference cost |
| --- | --- | --- | --- |
| 100 | 1,000 | 512 | $0.010668 |
| 1,000 | 1,000 | 512 | $0.10668 |
| 10,000 | 1,000 | 512 | $1.0668 |

Illustrative gross Lambda at 512 MB/five seconds, USD 0.0000166667/GB-second and USD 0.20/million requests, plus HTTP API at USD 1/million requests, yields:

| Queries/month | Bedrock | Lambda | HTTP API | Subtotal |
| --- | --- | --- | --- | --- |
| 100 | $0.010668 | $0.00419 | $0.0001 | $0.01495 |
| 1,000 | $0.10668 | $0.04187 | $0.001 | $0.14955 |
| 10,000 | $1.0668 | $0.41867 | $0.01 | $1.49547 |

These are workload subtotals, not all-in bounds: input includes resent history, and Lambda waits for inference. At 20 seconds its compute component quadruples; cold starts/retries can add usage. Measure Flask/adapter startup and 512-token generation rather than promising the five-second assumption.

For three turns with 100 new user tokens and 200 assistant tokens per answer, input is billed as 100, 400, then 700 tokens; total 1,200 input/600 output costs USD 0.000126 at reference rates, excluding system/template overhead. Longer histories increase costs. LocalStorage/copy/layout add no AWS database service.

The cost guide must include S3 bytes/requests, CloudFront bytes/requests/chosen plan, artifact storage, CloudWatch ingestion/retention, one-user Cognito, exclusions/taxes, and current sources. Start with CloudFront pay-as-you-go; verify recurring allowances without assuming flat-rate eligibility/provider support. Cognito Lite reference allowance is 10,000 direct/social MAU per account/organization, so one user costs USD 0 when available; the first paid band is USD 0.0055/MAU. Verify current terms and bootstrap/recovery email assumptions. No paid Plus/advanced security/SMS/M2M delivery, custom domain, WAF subscription, NAT, or provisioned concurrency is planned.

Assume zero promotional credits; document checking Billing Credits balance/expiration/applicability. Show gross prices separately from recurring allowances and unrelated account usage. Notification-only Budgets monitoring and IAM have no added service charge under published terms. Configure a USD 5 monthly COST budget filtered to verified service names for Bedrock, Lambda, API Gateway, Cognito, S3, CloudFront, and CloudWatch, excluding credits/refunds, with actual GREATER_THAN email alerts at 50/80/100%. Require a positive amount and valid recipient. No reports/SNS/budget actions. Account-wide service aggregation may include unrelated usage; notifications lag and do not stop calls.

## Risks / Trade-offs

- Model retirement/account restrictions: check availability and deliberately revise configuration/estimates if needed.
- Alert overspend/unknown credits: estimate full prices and disclose delay/lack of enforcement before deployment.
- Flask/LangChain/adapter size and cold starts: verify packaging limits and measure real duration.
- Browser persistence is device-local and script-readable: owner isolation, validation, explicit erase controls, safe rendering, and no persistent tokens.
- Coverage does not prove deployment behavior: retain meaningful negative-path tests and adapter/Chrome checks.
- Existing permissions outside managed roles and local state loss: document account boundaries and secure state backup/import.

## Migration Plan

No existing application requires migration. Implement locally and validate packaging, tests, types, and Terraform. Review prices/account/model and saved plan before authorized deployment. Bootstrap the sole owner without Terraform passwords, configure subject, then verify Chrome login/follow-ups/context notices, refresh/reopen, clear/logout erasure, copy/keyboard controls, and denial of unauthenticated/other-user requests. Check direct CLI/SDK access and budget settings. Record real usage/duration. Roll back through Terraform destroy only when requested; address frontend/artifact bucket contents and user-pool deletion, retain state, and explain that prior charges and unrelated access remain.

## Open Questions

- Profile, stable principal ARN, owner username/email, and alert email are deployment inputs; obtain owner subject during bootstrap.
- Eligible credits and expiry require billing access; full-price estimates remain usable without them.

## Sources

- [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
- [AWS Nova reference prices](https://d1.awsstatic.com/onedam/marketing-channels/website/aws/en_US/events/approved/reinvent-2025/reinvent/2024/slides/aim/AIM398-NEW_Practical-generative-AI-using-Amazon-Nova.pdf)
- [Nova Micro model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-micro.html)
- [Bedrock model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)
- [Cognito pricing](https://aws.amazon.com/cognito/pricing/)
- [Cognito clients and PKCE](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-client-apps.html)
- [HTTP API JWT authorization](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html)
- [LangChain Bedrock](https://docs.langchain.com/oss/python/integrations/chat/bedrock)
- [Lambda Web Adapter](https://github.com/aws/aws-lambda-web-adapter)
- [Lambda pricing](https://aws.amazon.com/lambda/pricing/)
- [API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/)
- [S3 pricing](https://aws.amazon.com/s3/pricing/)
- [CloudFront pricing](https://aws.amazon.com/cloudfront/pricing/)
- [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)
- [Budgets pricing](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/)
- [AWS Free Tier](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier.html)
- [Jest configuration](https://jestjs.io/docs/configuration)
- [pytest-cov configuration](https://pytest-cov.readthedocs.io/en/latest/config.html)
- [Vite environment variables](https://vite.dev/guide/env-and-mode)
