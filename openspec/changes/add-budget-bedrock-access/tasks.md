# Tasks

## 1. Cost guide and prerequisites

- [x] 1.1 Create `docs/bedrock-costs.md` with current sourced rates, 100/1,000/10,000-query estimates at 512 output tokens, conversation-history rebilling, Lambda duration sensitivity, and S3/CloudFront/API/logs/artifact/Cognito assumptions; verify arithmetic and distinguish gross costs, recurring allowances, and zero promotional credits.
- [x] 1.2 Document CLI/Terraform/Python/build prerequisites, credentials, account identity, regional model lifecycle/access checks, owner bootstrap, and deployment permissions; verify read-only preflight commands and place cost links before deployment instructions.

## 2. Terraform identity, infrastructure, and cost controls

- [x] 2.1 Add `infra/bedrock/` provider/version constraints, lock file, variables/examples/outputs and state/secret/build ignore rules; verify initialization, formatting, validation, and tracked lock files.
- [x] 2.2 Implement separate model-scoped CLI/Lambda roles and scoped log permissions; verify mocked tests reject broad grants/trust and document caller AssumeRole prerequisites.
- [x] 2.3 Provision Cognito Lite with self-registration disabled, hosted login, secretless code/PKCE client, exact callback/logout URLs, and custom query scope; verify policy assertions and document password-free Terraform bootstrap.
- [x] 2.4 Provision private S3 frontend storage and CloudFront OAC/HTTPS; verify tests deny direct public bucket access and document the public static shell.
- [x] 2.5 Provision JWT-protected POST query integration, issuer/audience/scope checks, restricted Lambda invocation, frontend-only CORS, 1 request/second burst-2 throttling, concurrency 1, bounded timeout, and seven-day logs; verify infrastructure tests cover bypass prevention and controls.
- [x] 2.6 Implement the accepted configurable USD 5 monthly budget across verified Bedrock/Lambda/API/Cognito/S3/CloudFront/CloudWatch service filters, excluding credits/refunds and notifying at 50/80/100%; verify positive-budget/email validation and explain aggregation/delay/no hard cap.

- [x] 2.7 Configure CloudFront Referrer-Policy no-referrer, nosniff, and enforced CSP for bundled same-origin scripts and required API/Cognito connections, blocking unsafe inline/eval, objects, framing, and unrestricted base URLs; verify infrastructure assertions. For enabled frontend/API/origin access logging, allowlist safe operational fields and exclude query strings, cookies, Authorization headers, and callback-bearing referrers; keep incompatible formats disabled and test configuration.

## 3. Flask Lambda, pytest coverage, and CLI/SDK access

Implementation checkpoint: CPython 3.14.8 is installed through pyenv and pinned
in `backend/.python-version`; backend/SDK offline tests pass with exact 100% statement
and branch coverage. Docker Desktop is running; the Linux/x86_64 ZIP build and
real Web Adapter HTTP API smoke checks pass locally. Source, tests, Lambda packaging, examples, scripts, and Pipenv dependency files
now live under `backend/`. No live deployment is verified.

- [x] 3.1 Implement the Flask factory/query route and injectable LangChain model service; verify follow-up tests preserve pair order, return complete text/usage, enforce 512 output tokens, make no search/tool calls, and avoid live AWS.
- [x] 3.2 Implement cached JWKS/signature/issuer/client/expiry/access-token/scope/owner validation independently of forwarded identity headers; verify pytest cases for invalid/expired/wrong-user tokens, key refresh failures, and missing owner make no model calls.
- [x] 3.3 Enforce current-prompt 4,000-code-point, 10-history-pair, 32,000-total-code-point, 256-KiB-body, and 512-output-token limits plus bounded retries/timeouts and safe logging/errors; verify Unicode/exact boundaries, malformed roles/history, client overrides, provider failures, and absence of secrets/messages in logs.
- [x] 3.4 Add temporary-profile CLI/boto3 examples defaulting to 512 output tokens; verify shell syntax and stubbed success/error behavior and document usage/cost interpretation.
- [x] 3.5 Package Flask/Gunicorn with pinned Lambda Web Adapter ZIP bootstrap/layer; verify Linux/runtime/architecture/size compatibility and request/header/body/status/error/readiness smoke cases with debug disabled.
- [x] 3.6 Configure pytest-cov over all first-party backend source including unimported modules with exact 100% statement/branch gates and XML/JSON reports; verify negative-path coverage and document commands/exclusions.

## 4. React/TypeScript/Vite frontend, Jest coverage, and onboarding

- [x] 4.1 Scaffold the typed frontend and pinned OIDC client with a labeled scrollable You/Assistant conversation, multiline composer, Submit, Clear conversation, Sign out, complete responses, loading/token/context/error feedback, and model-only note; verify React Testing Library behavior tests and session clearing.
- [x] 4.2 Add Vite production build/upload and runtime public-JSON config validation without application Vite-only globals; verify build, config error tests, root callbacks, required access-token scope, and secret-free assets.
- [x] 4.3 Document staged owner creation/password setup outside Terraform, immutable subject retrieval/configuration, fail-closed initial deployment, login/logout, and token-expiry limitations; verify instructions match outputs and no password enters state/source.
- [x] 4.4 Configure Jest TS/TSX transforms/source maps, jsdom/static mocks, and coverage of all executable application source including entry/storage/context code; verify exact 100% statements/branches/functions/lines globally/per-file with JSON/LCOV reports and no application coverage exclusions.
- [x] 4.5 Add strict types for messages/exchanges/API/usage/auth/settings/storage and runtime external-data validation; verify tests and independent `tsc --noEmit` type checking included in the build workflow.
- [x] 4.6 Implement owner-keyed versioned localStorage restore after authentication with newest-100-pair/1-MiB retention defaults and visible notices; verify refresh/reopen/owner-isolation/corrupt/unsupported/oversized/quota/unavailable-storage tests and document privacy.
- [x] 4.7 Implement newest-10-completed-pairs-plus-current-prompt context selection, dropping oldest whole pairs for total size without deleting saved messages; verify count/Unicode boundaries, order/notices, and no automatic replay.
- [x] 4.8 Implement clear/logout erasure, request-generation guards, and cross-tab removal handling; verify late responses/stale tabs cannot recreate erased messages and storage removal failures are visible.
- [x] 4.9 Add Copy answer for each completed assistant message with success after clipboard resolution and actionable unavailable/rejected fallback; verify exact answer-only copying, accessible feedback, zero model calls, documented controls, and retained 100% coverage.
- [x] 4.10 Implement Enter submission, Shift+Enter newline, IME composition protection, shared click/keyboard validation, in-flight guard, and scroll-position preservation; verify keyboard/duplicate/invalid-input/scroll tests and accessible statuses.

- [x] 4.11 Implement OIDC callback capture/validation and replacement of the current history entry with the clean root URL on success and failure, transient-state cleanup, and sanitized errors/logs; test successful, rejected-state, OAuth-error, and failed-exchange callbacks without accepting invalid authentication or retaining raw callback values.
- [x] 4.12 Verify prompts, answers, and restored HTML-like messages render as inert text without embedded requests; keep scripts bundled locally without analytics/third-party scripts, test tokens never enter localStorage and existing clear/logout erasure, and document that owner-keyed saved history is readable by same-origin scripts and someone with unlocked browser-profile access.

## 5. Integration and live account validation

Local implementation checkpoint (2026-11-09): 71 Python tests and 104 Jest tests
pass with exact 100% coverage; clean installs, strict types/Vite build, Linux
adapter smoke checks, and 10 Terraform mock runs pass. Both gates reject an
unimported probe file. The previous saved plan had 31 creates and zero updates/deletes. It was removed
because it retained identifying input values. Supply the trusted principal and
budget email through sensitive `TF_VAR_*` inputs and regenerate the plan before
deployment; the backend layout and ZIP path have also changed. STS identity and Nova Micro ACTIVE/on-demand/
AUTHORIZED/AVAILABLE status are verified. Regional token prices and seven
service labels are verified against public AWS catalogs. Live preflight is
blocked on `lambda:GetLayerVersion` for the pinned layer and
`lambda:GetAccountSettings`; the updated policy is in
`docs/iam/bedrock-preflight.json`. No infrastructure apply has run. Remaining
checkboxes require actual deployment/owner bootstrap/Chrome and billable checks;
local unit/mock results do not complete them. Jest's development dependency
advisories are documented in README.md; the GitHub workflow has not run remotely.

- [x] 5.1 Add CI for pinned installs, exact pytest/Jest coverage gates, types, Vite build, and Terraform checks; verify all locally, adapter packaging, and failure on uncovered files, plus no provisioned throughput/public query bypass/broad grants/NAT/provisioned concurrency.
- [ ] 5.2 Once implementation is requested and account inputs exist, verify account/model/prices, review a saved Terraform plan, and deploy when authorized; verify outputs/budget filters/state handling and record blocked account checks as incomplete.
- [ ] 5.3 Bootstrap the sole owner and verify in Chrome login/follow-ups/complete answers/usage/refresh/reopen/context notices/clear/logout/copy/Submit/Enter/Shift+Enter; verify no-token/expired/wrong-scope/other-subject requests cannot invoke Bedrock while public visitors see only the shell.
- [ ] 5.4 Run bounded live CLI/SDK checks, measure Flask/adapter duration, asset traffic, usage/answer quality at 512 output tokens and model-only behavior, and refine estimates; review teardown limited to managed resources including bucket contents/user pool, performing destroy only when requested.

- [ ] 5.5 Verify deployed security headers and CSP enforcement in Chrome while login/query remain usable; check callback cleanup on success/failure and Back navigation, referrer suppression, and absence of synthetic callback markers in enabled access logs. Keep these deployment checks separate from unit coverage claims.
