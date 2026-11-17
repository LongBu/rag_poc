# Azure migration verification evidence

> Privacy: account names, application origins, image digests and request IDs in this document are synthetic placeholders; replace them before use.

November 16, 2026. This records completed local/preflight checks separately from
unrun live acceptance. It is not a claim that the application has been migrated
or deployed.

- Azure CLI read-only subscription/Graph/catalog/quota/billing/budget-list checks
  succeeded; see `azure-setup.md`. Billing currency is USD. Regional public price
  comparisons and arithmetic are recorded in `azure-costs.md` and the sanitized
  public `azure-price-evidence.json`.
- AzureRM 4.81.0 is pinned exactly; committed provider lock covers darwin_arm64
  and linux_amd64. Terraform 1.17.0 formatting/validation pass. Seventeen mocked
  model-root runs pass, including account scope, disabled key authentication,
  model/version/SKU/capacity, outputs, group budget, all three thresholds and
  invalid UUID/email/currency/date/region/capacity/budget inputs. Mock apply/test
  does not contact Azure or prove actual deployment acceptance.
- A real read-only model-stage Terraform plan proposes five creates, no changes
  and no destroys: dedicated resource group, OpenAI account, GPT-5 mini deployment,
  account-scoped developer role, and RG budget. No app resources or registry are
  present. That plan has now been applied for task 2.7; see `azure-model-access.md`
  for actual model/budget/RBAC/probe evidence. Consumed plans must not be reused.
- CPython 3.14.8 is retained. Pinned `langchain-openai==1.8.0` and
  `azure-identity==1.27.0` replace the AWS model dependencies. Pipenv lock verify
  succeeds. Clean dev and separate production-only installs succeed; production
  imports Azure code without pytest, boto3 or botocore. Both environments pass
  `pip check`. Coverage settings and production/development separation are
  unchanged.
- Backend tests after task 4.3: 261 pass; exact statement and branch coverage are 100%, with
  zero missing lines or branches. Tests include history/system-message order,
  both explicit credential choices, no ambient-key fallback, fixed parameters,
  timeout/retry limits, empty/refusal/invalid usage, sanitized provider failures,
  status/request IDs, readiness configuration, CLI success/failure and shell
  wrappers. A real pinned SDK over `httpx.MockTransport` verifies the Azure URL,
  Entra Bearer header, API version and serialized GPT-5 mini request parameters
  without acquiring a real token or invoking a real model.
- Task 3.1 backend Entra authentication and Flask wiring are implemented; see
  `azure-auth.md` for the runtime input contract and adversarial authentication
  tests. Every rejected-token test asserts zero model calls. No cloud resources
  or live model invocations were changed/performed for this task.
- Task 3.2 public frontend Azure config validation is implemented; see
  `azure-frontend-config.md`. All 169 frontend tests pass across six suites with
  exact 100% statement/branch/function/line counters. Strict TypeScript and Vite
  production build pass. Tasks 3.3/3.4 also verify Entra OIDC claim/logout behavior and tenant/object-ID
  history identity wiring (`azure-browser-auth.md`, `azure-history.md`); actual
  browser login and hosting are still pending.
- Task 4.1 same-origin shell, hashed assets, public runtime config and enforced
  security headers pass route/cache/traversal/symlink/secret-exclusion tests; see
  `azure-web.md`. The actual Vite build also passes a Flask test-client smoke
  check without cloud access. Image-layer verification remains task 4.6.
- Task 4.2 per-process concurrency and one-per-second/burst-two admission
  controls pass deterministic refill, overlap, readiness and release-on-error
  tests. One-worker/four-thread Gunicorn configuration validates locally; see
  `azure-admission.md`. Real container HTTP checks now pass under task 4.3; live load checks remain pending.
- Task 4.3 pinned Linux/amd64 multistage image builds successfully, including
  locked production installs and strict frontend build. Real Gunicorn HTTP
  smoke tests pass with non-root/read-only runtime, writable temporary storage,
  no network, synthetic auth/model services and sanitized stderr. See
  `azure-container.md`; publication and full layer review remain pending.
- Dependency deprecation warnings from LangSmith's asyncio helper and a test-only
  runpy module-reexecution warning remain. They do not weaken coverage gates.

Not performed: actual budget email delivery, Entra SPA/API registration, live browser sign-in and acceptance,
Container Apps infrastructure, full image-layer review, GHCR publication,
app deployment, Azure cost visibility and teardown. The frontend, Entra registrations and hosting still require the remaining Azure
migration tasks. Do not deploy this
intermediate application as the completed Azure app. Original AWS planning,
private state/backups and AWS resources have not been removed or destroyed.

## Private-input review

Actual subscription/tenant/object IDs and the budget email are external inputs,
not committed defaults. A scan of all 99 current Git-visible files found no
matches to the actual private deployment identifiers/email and no high-confidence
private-key/GitHub/OpenAI/AWS credential markers. This is a current-working-tree
check, not a repository-history audit or a guarantee about every possible secret
format. Examples and mocks retain fake identifiers and placeholder email.
Budget email is now sensitive in Terraform console output. Local input, saved
plan and text-export files use owner-only permissions; Git also ignores `.azure/`
login caches. State/plans still contain parameter values and must stay private.
The privacy review itself authorized no apply or inference. The owner subsequently
authorized task 2.7; see `azure-model-access.md` for that separate live result.
See `azure-setup.md` for local tfvars/environment configuration.

## App-root implementation, November 16, 2026

Tasks 4.4/4.5: app-root formatting and validation pass, with 20/20
credential-free Terraform mock runs passing. AzureRM 4.81.0/AzureAD 3.10.0
locks include macOS ARM64 and Linux AMD64 checksums. Tests cover staging,
account-scoped inference identity, public digest/no-registry-secret delivery,
Consumption/zero-to-one replicas, HTTPS/probes, exact public runtime settings,
single-tenant v2 delegated scope/preauthorization and generated SPA callbacks.
Only the intended identity/role/environment/app Azure resource types are declared;
shared group/model/budget remain in the model root. See `azure-app.md`.

Task 4.6 preparation: review-image self-check and actual full image review pass:
nine layers, 13,417 files, configuration and untruncated history reviewed for
private artifacts and high-confidence secret markers. See `azure-release.md`
for the exact local image ID, limitations, current GitHub pricing sources and
explicit publication/anonymous-pull procedure. No public image target was
supplied, and no push, tenant bootstrap, hosting apply, actual managed-identity
inference or browser/cost acceptance was performed. Task 4.6 remains unchecked;
tasks 5 and 6 have not been executed in this session. Existing backend/frontend
coverage and container smoke evidence was not rerun because runtime source did
not change.

## Public GHCR verification, November 16, 2026

The owner published the reviewed image under `ghcr.io/example/private-azure-chat`
and set its visibility to public. Independent anonymous pulls succeeded for
the release tag and exact immutable digest, using empty temporary Docker
credential configs with the existing Desktop daemon endpoint. The pulled
Linux/amd64 image matches the reviewed local image. Its nine layers/13,417 files
and metadata/history passed another review by exact registry digest. The
reference and verification details are recorded in `azure-release.md`. No
publication credential was read by the agent. Hosting/identity apply and live
managed-identity/browser/cost acceptance remain pending.

Read-only Azure account and signed-in directory identity checks succeeded.
Subscription/tenant match existing model outputs. Fresh private app inputs
and the identity-only bootstrap saved plan agree on every supplied value.
The plan has exactly 12 creates (Entra registrations/principals/scope/client
relationship plus runtime identity/account-scoped inference role), no changes
or destroys, and no hosting/model/group/budget resources. Private inputs and
plan/text export have owner-only permissions and are Git-ignored. Bootstrap
apply remains pending review; no billable inference was invoked.

## Approved identity-only bootstrap apply, November 16, 2026

After explicit owner approval, the exact saved bootstrap plan was rechecked
against all current private inputs and the approved 12 create-only resource
addresses. Apply succeeded: 12 added, zero changed/destroyed; hosting stayed
disabled. Azure/Graph readback independently confirmed both single-tenant v2
applications and enabled service principals, disabled implicit grants, no app
passwords/keys, the sole delegated query scope, exact SPA preauthorization/API
access, and absent placeholder callbacks/logout. Runtime managed identity and
its Cognitive Services OpenAI User role at the dedicated model account were
verified. Real managed-identity inference, hosting and browser/cost acceptance
remain unperformed. The consumed bootstrap plan must not be reused; private
state/logs are retained. OpenSpec tasks 4.6/6.1 remain unchecked because their
remaining live checks are not satisfied by identity creation alone.

The post-apply read-only Terraform plan returned exit code 0 with no changes.

## Azure CI/setup replacement and offline validation

Tasks 5.1–5.3 were verified locally after the identity bootstrap. The workflow
now builds the pinned Linux/amd64 container, runs real network-isolated Gunicorn
HTTP smoke tests and layer-review/self-check, and runs init with read-only locks,
formatting, validation and mocked tests for both Azure roots. Exact coverage
counters, strict TypeScript/Vite and read-only repository permissions remain.
The workflow has no cloud credentials, publisher login/push or deployment step.
YAML parsing and shell syntax checks pass; GitHub Actions itself has not run.

A fresh temporary Pipenv environment installed locked development dependencies
on CPython 3.14.8 and passed all 261 tests with exactly 100% statement/branch
coverage (zero missing lines/branches). The existing checkout's virtualenv has
old executable shebangs from its former location, so pytest is invoked through
`pipenv run python -m pytest`, matching the clean run and avoiding that stale
script path. No interpreter/dependency or coverage configuration was changed.
A clean npm install passed all 169 frontend tests, with exact 100% statement,
branch, function and line coverage; strict TypeScript and Vite build passed.
Both Python and frontend gates were deliberately tested with temporary unimported
uncovered source; both failed as required. Probe files were removed and isolated
probe reports did not replace the baseline coverage artifacts.

The container build passed (cached production install/build layers), followed
by actual read-only/non-root, no-network production/mocked HTTP smoke checks.
Image review passed nine layers/13,417 files plus config/history, with its
self-check passing. This local build refreshed the local tag only; the published
GHCR release and private Terraform image reference were not changed or pushed.
Model Terraform: 17/17 mock runs; app Terraform: 20/20; both pass formatting,
validation and lock-readonly initialization. Public config fields, tenant/API/SPA
IDs, delegated query scope, owner identity, same-origin URL and managed-identity
settings were compared across frontend/backend/Terraform; their existing route,
auth, config and mock contract tests pass.

README now describes Azure account/setup, separate model/app permissions,
container checks, public GHCR release, reviewed activation, privacy, costs,
rollback and app-before-model teardown. Active examples already use Azure CLI
credentials and the Entra SDK boundary. The obsolete tracked AWS Terraform, IAM
documents, cost guide, Lambda adapter/ZIP build and emulator fixtures were
removed (26 tracked files). Historical AWS OpenSpec artifacts and private AWS
state/backups were inventoried by SHA-256 and verified unchanged after cleanup.
Active paths require no AWS credentials/endpoints; the only AWS-prefixed smoke
assertion rejects such variables in an image. The retained `bedrock_chat` import
path and package metadata are documented. No AWS SDK dependencies remain in
the production lock. Updated documentation links and `git diff --check` pass.

No apply, model invocation, image publication, GitHub workflow run or live
browser/security/scaling/cost acceptance was performed for this cleanup. Tasks
4.6 and 6 remain unchecked for the outstanding live checks.

## Task 6.1 activation plan prepared

Read-only activation preflight confirms the selected enabled subscription,
tenant and signed-in owner still match model/app inputs. Required Microsoft.App,
ManagedIdentity and CognitiveServices providers are registered. Current regional
ManagedEnvironmentCount is zero used of one permitted; this allowance does not
guarantee placement capacity. Billing remains USD; the existing shared-group
monthly budget is still 5 with actual 50/80/100 notifications and the configured
private recipient. The exact published digest still pulls anonymously using an
empty Docker credential configuration.

Microsoft Retail Prices API was queried again for the exact East US 2 meter IDs.
Global Standard GPT-5 mini input/cached/output, Consumption CPU/memory/requests
and internet-egress tiers match the recorded guide. Current Microsoft billing
documentation still lists the shared monthly Consumption grants and zero
replica consumption charge at scale-to-zero. GitHub's current billing policy
still states container storage/bandwidth are free, with publisher/build charges
separate. No unused grant or promotional credit is assumed in gross estimates.

Fresh owner-only ignored activation inputs set `deploy_app=true` and retain the
verified published digest and existing owner/model/identity settings. The saved
`infra/azure/app/activation.tfplan` and private text export propose exactly three
creates (Consumption environment, Container App, SPA callback resource), one
update (existing SPA logout URL), zero deletes. Every supplied input was compared
to the saved plan. Planned runtime settings preserve 0.25 vCPU/0.5 GiB, min zero/
max one, single revision, HTTPS, managed identity, no registry credentials and
no retained logs. Existing model/group/budget and bootstrap identities remain.
Activation has not been applied; current plan/cost review is pending owner
approval. Tasks 4.6/6.1 and live acceptance remain incomplete.

## Hosting activation applied; owner acceptance pending

The explicitly approved saved activation plan applied successfully: three
added, one updated, zero destroyed. Public HTTPS shell/readiness/config return
200; anonymous and forged-token query calls return 401. Deployment readback
verifies the exact public digest, user-assigned identity, HTTPS-only ingress
and absent registry credentials. Entra callback/logout URLs equal the generated
site root; public runtime config matches owner/tenant/client/scope/origin inputs.
Canonical private inputs retain activation; a fresh post-apply plan reports no
changes. See `azure-release.md` for the site and detailed evidence.

Azure's console returned 503 before the synthetic managed-identity probe could
run. A bounded non-inference console check also failed. No successful console
model invocation is claimed. Actual owner browser sign-in/Hello result is
pending user verification. Tasks 4.6/6.1 stay unchecked; this deployment alone
does not establish their complete acceptance or any remaining live task.

## Owner confirms live login and response

The owner subsequently reported successful live use: a `Hello.` prompt returned
`Hi — how can I help you today?`, with Copy answer visible. This user-reported
browser result verifies the deployed owner login/inference path when combined
with the independently read-back managed-identity-only runtime and owner-token
contract. Tasks 4.6 and 6.1 can now be checked. The management-console probe did
not run and is not counted as a success. Token usage was not supplied in this
report; broader browser/security/scaling/cost acceptance remains unchecked
under tasks 6.2–6.4.

## User-reported browser checks for task 6.2

The owner reported that Clear conversation works; Sign out/Sign in works;
bounded follow-ups and complete text/token usage work within the configured
limits; and messages reappear in order after closing/reopening the app and
signing back in. Refresh returns to sign-in, consistent with in-memory auth
tokens. The incognito automatic-sign-in concern was withdrawn after the owner
confirmed Sign out/Sign in works; no authentication policy was changed and
its original cause was not established.

These are user-reported results, not an agent-controlled browser trace. Reopen
restoration is confirmed. Refresh restoration was not separately confirmed.
Retention/context notices, cross-tab and late-response erasure, copy feedback,
Enter/Shift+Enter/IME, scrolling, and the complete live rejected-token matrix
remain unverified. Task 6.2 stays unchecked until all its specified checks pass.

The owner additionally confirmed that Copy answer works. Clipboard failure
feedback was not separately tested; task 6.2 remains partially complete.

The owner confirmed refresh restoration passes: after refresh and sign-in,
saved messages restore. This resolves the previously unconfirmed refresh
restoration check; task 6.2 remains open for its other outstanding checks.

The owner confirmed the model-context notice passes in the live browser.
The separate 100-exchange/1 MiB storage-retention notice remains unverified.
Task 6.2 remains open for its other outstanding checks.

The owner confirmed that cross-tab clear/logout and late-response clearing
pass in the live browser. Task 6.2 remains unchecked pending storage-retention
notice, keyboard/IME, scrolling, and the remaining live rejected-token checks.

The owner confirmed that keyboard/IME behavior and scrolling pass in the live
browser. The remaining task 6.2 checks are the storage-retention notice and
the full live rejected-token matrix; task 6.2 remains unchecked.

## Controlled retention fixtures and supported live token checks

Prepared `frontend/tests/manual/retention.js` with count and byte modes and
`check-retention.cjs` as its assert-based self-check. Count seeds 100 valid
synthetic exchanges; bytes seeds 12 exchanges at exactly 1 MiB minus one byte.
The large oldest answer stays outside the ten short pairs sent to the model.
Fixtures refuse to overwrite any existing history/generation state; the
self-check verifies both boundaries, bounded model context and that refusal.
Manual disposable-profile steps are in `azure-manual-retention.md`. Actual
retention-notice/reopen UI results are still pending user execution; no browser
data was altered by the agent and no model requests were made for fixture prep.

Executed `backend/scripts/check-live-auth.py` against the deployed API. All
eight cases returned 401: missing bearer, malformed bearer, forged identity
headers, unsigned alg=none, disallowed HS256, RS256 missing kid, invalid RS256
signature using a Microsoft kid, and a real Microsoft-issued developer token
for Cognitive Services rather than this API/SPA. Azure CLI acquired that token
using existing permissions; it stayed in memory and was never printed/saved.
Every POST used an invalid empty prompt so validation would prevent inference
even if authorization unexpectedly succeeded. No inference was made.

The real wrong-resource token differs in several claims; this is not isolated
proof of every claim rejection. Legitimately issued suitable tokens for isolated
expiry/nbf, ID-token, missing-query-scope, other tenant/client/owner and app-only
API-token cases were not available. No new identities/registrations/permissions
were created. Those live cases remain open, with offline adversarial coverage
retained. Task 6.2 remains incomplete; no acceptance criteria were dropped.

The owner reported the live notice "1 older exchanges removed by the storage
retention limit." and confirmed reload/sign-in preserves the trimmed transcript.
The last shared fixture used count mode, but the owner has not explicitly
identified the mode for this result; do not count both boundaries as verified.
The separate boundary result and remaining live token cases remain open.

The owner clarified that the successful live retention notice and persistent
trimmed transcript result used count mode. The 100-exchange boundary is now
verified; the separate 1 MiB bytes-mode browser check remains pending.

The owner confirmed the live bytes-mode retention test is validated. Both the
100-exchange and 1 MiB retention boundaries now have user-reported live passes.
Task 6.2 remains open only for the outstanding isolated live rejected-token
cases; no additional identities, registrations or credentials were created.

## Owner-approved task 6.2 acceptance scope revision

The owner explicitly requested removing the unavailable isolated live
rejected-token cases from task 6.2 and considering the task complete. The
task and design now require the completed user-reported browser checklist,
eight representative live 401 checks using available credentials and full
offline adversarial token-claim coverage. Task 6.2 is complete under that
revised scope. Isolated live expiry/nbf, ID-token, missing-scope, other
tenant/client/owner and app-only API-token cases remain unverified, not passed.
No runtime auth requirements, implementation, tests or permissions changed.
Tasks 6.3 and 6.4 remain incomplete.

## Task 6.3 partial live privacy/readiness evidence

Read-back confirms live-only logging (no retained log destination). Delivered
headers match no-referrer, nosniff, frame denial and one-year HSTS. Delivered
CSP includes default/script/style self restrictions, exact tenant discovery/
token connection endpoints, frame/base/object/form restrictions and upgrade
insecure requests, with no unsafe-inline/unsafe-eval. Browser enforcement and
callback cleanup/Back checks still require actual browser execution.

The initial live revision had one replica. First measured HTTPS readiness
round-trip: 0.144 seconds; subsequent warm
round-trips: [0.111, 0.111, 0.106] seconds. These are
warm endpoint timings, not cold-start/model latency. After synthetic callback/
state and denied prompt marker requests, live console readback returned two
entries and contained none of those markers or bearer credentials. No inference
was made. This bounded log sample is not a claim about every historical/platform
log. Gunicorn access logging remains disabled in the reviewed deployed image.

Prepared test-only browser CSP and synthetic overlap/timing probes, with
assert-based helper checks passing for cleanup, two-request limit, response
preservation and no secret output. Instructions are in `azure-manual-privacy.md`.
The overlap probe permits at most two billable normal-cap synthetic requests
and does not automatically retry. It has not yet run in the browser. Task 6.3
remains unchecked while scaling and browser/inference checks are incomplete.

## Observed scale-to-zero and cold readiness

The same live ready revision reported zero replicas at the 395-second idle
observation. A single following HTTPS `/ready` request woke the app and returned
200 in 39.034 seconds. This is an observed zero-replica-to-HTTPS-readiness round-trip,
including front-door/network/container startup, not isolated model compute or a
latency guarantee. Warm readiness samples were 0.106–0.144 seconds. The configured
300-second cooldown did not imply exactly 300-second observed scale-down.
Management-only reads did not deliberately send app traffic during the idle
window. One secondary replica read raced with the wake-up and saw a not-yet-ready
replica; the readiness request subsequently completed successfully.

No model call was made for agent-run task 6.3 checks. Available request metrics
showed early-window traffic then zero-valued buckets, but metrics can lag and
the initial CLI query's implicit time window was not a complete traffic audit.
Scale-to-zero does not cap monthly spend; startup/scale-down tails and repeated
wake-ups can incur charges. Browser CSP enforcement, callback success/error/
Back cleanup, inference round-trip and overlapping-request rejection remain
pending the prepared Chrome probes in `azure-manual-privacy.md`. Task 6.3
remains unchecked, and task 6.4 is unchanged.

The owner supplied the live Chrome CSP probe result: inline-script and
disallowed-connection attempts were blocked by script-src/connect-src, and
the probe printed its PASS message. Browser CSP enforcement is confirmed.
The expected violation messages are evidence of blocking, not app failures.
Callback cleanup/Back navigation and inference/overlap timing remain open
for task 6.3. No private tenant identifier from the console output is copied
into this evidence.

The owner confirmed that the app URL after successful sign-in is the clean
root, without callback query parameters or a token fragment. Successful
callback cleanup passes. Synthetic failed-callback cleanup and Back-navigation
behavior remain unconfirmed, as does inference/overlap timing for task 6.3.

The owner supplied the live synthetic overlap probe result: HTTP statuses
[200, 429], batch round-trip 1.006 seconds, with the PASS message for one
completed answer and one throttled overlap. This confirms live overlap
rejection and records end-to-end batch timing; it is not isolated model
compute latency. The displayed 429 is expected. Failed-callback cleanup and
Back navigation remain outstanding for task 6.3.

The owner confirmed Back navigation after successful sign-in returns to the
clean app root. The synthetic failed-callback/Back check also leaves the clean
root without callback parameters. Both URL-cleanup/Back checks pass. The
report did not explicitly confirm the failed-callback feedback text; the app
error feedback is covered offline, while its exact live display remains
unconfirmed. Task 6.3 otherwise has delivered/enforced CSP/privacy headers,
bounded live log-marker scan, warm/cold readiness, scale-to-zero and live
inference/overlap timing evidence recorded above.

Task 6.3 is complete: its callback criterion is URL cleanup on success/error
and Back navigation, now confirmed, rather than exact feedback wording.
Measurements remain individual observations, the log scan is a bounded
sample, and scaling/admission controls are not a monthly spending cap.

## Task 6.4 budget, cost and lifecycle review (partial)

Budget readback passes group scope, USD 5/month, actual 50/80/100 enabled and
the private configured recipient. Cost Management initially returned 429; one
bounded retry succeeded with a single USD 0.000042 Foundry Models row dated
November 16. This equals the documented 24-input/18-output-token probe estimate.
No Container Apps row or later model charges were returned, so hosting/later
usage reconciliation is not yet established. Detailed evidence stays in an
owner-only Git-ignored log. Tokens used for read-only APIs remained in memory.

The owner reported GitHub account-level November metered usage: listed gross
$0.13, billed $0 ($0.07/$0, $0.04/$0 and $0.02/$0 on November 2, 3 and 10).
Product/repository attribution was not supplied and is not inferred. Current
registry policy remains separate from actual build/publisher usage; local builds
were observed but GitHub run/billing API access was unavailable. A public Actions
endpoint returned 404, not proof of zero runs.

`azure-operations.md` records these results, reconciliation arithmetic, current
and retained rollback digests, fresh-plan rollback, app-before-model teardown,
state retention and separately requested GHCR version cleanup. No destructive
action was taken. Task 6.4 remains unchecked for actual hosting/later-inference
cost visibility and matching usage reconciliation; no missing data is treated
as zero cost or silently accepted as verified.

## Azure teardown (November 17, 2026)

The owner authorized full project teardown. Both Terraform roots now have empty
state. Azure confirms the `private-azure-chat` resource group and the inventoried
Foundry account/project are absent. App, identity, model deployment, account,
budget and scoped role were removed. Private state and input backups remain.
The GHCR API delete returned 403 for missing `delete:packages` and
`read:packages` token scopes; the owner subsequently deleted the package through
GitHub package settings. A follow-up Cost Management query after teardown
recovered model meter-level usage for November 16–17, totaling USD 0.00915125
(7,069 input and 3,692 output tokens). No Container Apps meter row appeared;
that is not proof of zero hosting cost. GitHub product/repository attribution
and final post-close Azure cost reconciliation remain open under task 6.4; see
[`azure-operations.md`](azure-operations.md).

## Task 6.4 billing recheck (November 17, 2026)

The owner-provided GitHub usage CSV attributes four Linux Actions minutes on
November 10 to `rag_poc` / `.github/workflows/checks.yml`: $0.024 gross,
$0.024 discount, $0 net. The other two rows belong to another repository;
all three total $0.126 gross (rounding to the earlier $0.13), fully discounted.
Row quantities/rates and gross-minus-discount arithmetic pass decimal checks.
Authenticated Actions readback lists two November 10 checks runs, one success
and one failure. The billing API still returns 404; the supplied CSV provides
the attribution instead. Its full reporting range and final monthly completeness
are unverified. No registry usage row appears in this export.

A fresh project-filtered Azure cost query returned the same four model meter
rows, USD 0.00915125, and no next page. Decimal reconciliation of 7,069 input
and 3,692 output tokens passes at the estimated rates. Hosting still has no
returned meter row; neither zero cost nor free-grant coverage is established.
Task 6.4 stays unchecked pending actual hosting evidence and delayed/final cost
reconciliation. The explicit remaining checklist and corrected post-teardown
rollback status are in `azure-operations.md`. No destructive action or inference
was performed. The owner's raw billing CSV remains outside the repository.

## Task 6.4 closed by owner acceptance (November 17, 2026)

The owner explicitly approved closing task 6.4 on the assumption that total
project Azure costs were below USD 5 given the small usage. This is an accepted
closeout assumption, not a newly verified billing result. Verified evidence
remains USD 0.00915125 in model charges and USD 0.024 gross / USD 0 net in
repository-attributed GitHub Actions usage.

The owner-approved completion scope no longer requires actual hosting-cost
attribution, final Azure billing reconciliation or final monthly GitHub report
coverage. Those checks remain unverified, as does budget email delivery; the
uncompleted evidence checkboxes remain unchecked. Earlier statements that task
6.4 was open describe the status before this acceptance. Task 6.4 is now complete
and the change has 27/27 tasks complete. No resources, billing settings, retained
state or packages were changed for closeout.

## Pre-commit container and service status recheck (November 17, 2026)

The current Dockerfile built successfully for Linux/amd64 using cached build
steps. Container HTTP smoke tests passed for production and mocked targets,
including non-root/read-only operation, assets/configuration/readiness,
authentication rejection, input validation, safe errors, concurrency rejection
and sanitized logs. The image-review self-check and all-layer review passed:
nine layers and 13,417 files plus image configuration/history. This was a local
build; no image was published.

Read-only Azure checks confirmed that the selected subscription and tenant
match the private project inputs, the project resource group is absent, and
no matching API or SPA app registrations remain. The GitHub repository is
accessible; the package lookup returns HTTP 404 (not found), consistent with
the reported package deletion.

The README now reflects task 6.4's owner-accepted closeout. No resources were
recreated or billable inference performed. Live login, managed-identity
inference and anonymous image pulls cannot be repeated against the deleted
deployment/package. Final billing reconciliation and budget email delivery
remain unverified under the accepted scope.
