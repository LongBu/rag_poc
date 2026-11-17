# Azure setup and staged deployment

Verified November 16, 2026. Read this with [the cost estimate](azure-costs.md).
No model invocation, resource creation, image publication, or deployment was
performed by the preflight checks below.

Model-only deployment and a successful 32-token probe are now recorded in
[the live model evidence](azure-model-access.md). The checks below describe the
preflight workflow; app hosting and browser authentication remain pending.

## Install and select the account

On macOS, install the [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-macos)
with `brew update` and `brew install azure-cli`. Use browser login with MFA for
this personal Microsoft account; do not put passwords or access tokens in files.
A subscription and an Entra directory are different permission boundaries.

```sh
az login --tenant '<tenant-id>'
az account list --query '[].{name:name,id:id,tenant:tenantId,state:state}' -o table
az account set --subscription '<subscription-id>'
az account show --query '{subscription:id,tenant:tenantId,state:state}' -o json
az ad signed-in-user show --query '{id:id,userType:userType}' -o json
```

Use the returned directory object ID as the owner, not an email address, personal
account identifier from another tenant, or former Cognito subject. A personal
account must have a member/guest representation in the selected tenant. Test its
actual SPA login later; directory administration alone does not prove login works.
See [interactive login](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli-interactively).

For the following **read-only** checks, set `SUBSCRIPTION_ID`, `TENANT_ID`,
`OWNER_OBJECT_ID`, and `LOCATION` locally. Do not commit private tfvars, state,
plans, login caches, or full billing responses.

```sh
export SUBSCRIPTION_ID='<subscription-id>'
export TENANT_ID='<tenant-id>'
export OWNER_OBJECT_ID='<directory-object-id>'
export LOCATION='eastus2'
az role assignment list --assignee "$OWNER_OBJECT_ID" \
  --scope "/subscriptions/$SUBSCRIPTION_ID" \
  --query '[].{role:roleDefinitionName,scope:scope}' -o json
az rest --method get --url 'https://graph.microsoft.com/v1.0/policies/authorizationPolicy' \
  --query 'defaultUserRolePermissions.allowedToCreateApps' -o json
az rest --method get --url 'https://graph.microsoft.com/v1.0/me/memberOf/microsoft.graph.directoryRole' \
  --query 'value[].displayName' -o json
az provider list --subscription "$SUBSCRIPTION_ID" \
  --query "[?namespace=='Microsoft.CognitiveServices' || namespace=='Microsoft.App' || namespace=='Microsoft.Consumption' || namespace=='Microsoft.ManagedIdentity'].{provider:namespace,state:registrationState}" -o table
az cognitiveservices model list --subscription "$SUBSCRIPTION_ID" --location "$LOCATION" \
  --query "[?kind=='OpenAI' && model.name=='gpt-5-mini'].model" -o json
az rest --method get \
  --url "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/providers/Microsoft.CognitiveServices/locations/$LOCATION/usages?api-version=2025-06-01" \
  --query "value[?contains(name.value, 'gpt-5-mini')].{name:name.value,used:currentValue,limit:limit}" -o json
az rest --method get \
  --url "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/providers/Microsoft.App/locations/$LOCATION/usages?api-version=2025-07-01" -o json
az rest --method get \
  --url "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/providers/Microsoft.Billing/billingProperty/default?api-version=2024-04-01" \
  --query '{currency:properties.billingCurrency,status:properties.subscriptionBillingStatus}' -o json
az rest --method get \
  --url "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/providers/Microsoft.Consumption/budgets?api-version=2024-08-01" \
  --query 'value[].name' -o json
```

Model catalog and usage APIs are documented in Microsoft's
[model list](https://learn.microsoft.com/en-us/rest/api/aifoundry/accountmanagement/models/list?view=rest-aifoundry-accountmanagement-2025-06-01)
and [quota list](https://learn.microsoft.com/en-us/rest/api/microsoftfoundry/accountmanagement/usages/list?view=rest-microsoftfoundry-accountmanagement-2025-06-01).
Model quota units are thousands of tokens per minute. Neither quota nor listing a
SKU reserves capacity. Container Apps environment quota is separate from model
quota and does not prove app-level CPU/memory capacity or regional placement.

## Permissions and observed readiness (preflight snapshot)

| Check | Observed November 16 | Remaining verification |
| --- | --- | --- |
| Subscription | Enabled, FreeTrial offer, spending protection On | Credit remaining and expiry effects; do not remove protection automatically |
| Billing | USD; active subscription billing | Actual invoice/meter visibility after the first authorized probe |
| Provisioning identity | Subscription Owner | Actual resource creation and scoped inference role assignment |
| Entra directory | Global Administrator; app creation allowed | Actual registrations, delegated consent, personal-account SPA sign-in |
| Providers | CognitiveServices, App, Consumption registered | ManagedIdentity not registered; register before app bootstrap |
| OpenAI model | GPT-5 mini 2025-08-07, GA, chatCompletion capability; retirement 2027-07-13 | Deployment acceptance and bounded usable-text inference |
| Model quota (each compared region) | GlobalStandard 1,000 units unused; DataZoneStandard 300 unused | Physical capacity and model-account access |
| Hosting quota (each compared region) | One unused managed environment; 10 SandboxCores | Consumption workload and actual per-environment quota; SandboxCores alone is insufficient |
| Budget API | Subscription budget listing succeeds, no existing budgets | Create and read back the project RG budget and recipient before inference |

These are live read-only observations, not a deployment-readiness claim.
Global Administrator is an observed directory role, not a requirement to retain
permanently. App registration/consent permissions are distinct from Azure RBAC:
subscription Owner does not by itself grant Graph application administration.
If directory calls or consent fail, ask the tenant administrator for the needed
application creation/consent permissions. If resource provisioning or role
assignment fails, check Azure RBAC separately. Runtime identity needs only
`Cognitive Services OpenAI User` at the dedicated model account. That role is
account-wide, broader than a single deployment; use a dedicated account.

Provider registration is a **subscription write**, not part of read-only preflight:
review `az provider register --namespace Microsoft.ManagedIdentity --wait` before
app bootstrap. Retained logs are disabled, so OperationalInsights registration is
not a prerequisite for this design. Do not register every provider automatically.

## Private deployment inputs

The subscription ID, Entra tenant ID, developer object ID and budget email are
required Terraform input variables without real-account defaults. The committed
`infra/azure/model/terraform.tfvars.example` contains only fake UUIDs and
`owner@example.com`; it must never contain personal values. Mock tests use fake
values as well. Tenant/client/object IDs identify resources and identities; they
are not passwords. Some tenant/client identifiers will necessarily be public in
the browser sign-in configuration. The budget email is personal data and is
marked `sensitive` to redact it from normal Terraform plan/apply output.

Create local inputs from the placeholder example, restrict access, and edit the
local copy. Run from the repository root:

```sh
cp infra/azure/model/terraform.tfvars.example infra/azure/model/private.tfvars
chmod 600 infra/azure/model/private.tfvars
# Edit private.tfvars locally; do not paste passwords, API keys or tokens into it.
git check-ignore infra/azure/model/private.tfvars
```

Alternatively supply these same variables with `TF_VAR_subscription_id`,
`TF_VAR_tenant_id`, `TF_VAR_developer_object_id`, and `TF_VAR_budget_email` from
your local environment. Avoid putting personal values directly in command-line
`-var` arguments or committing shell scripts containing real values. Public
examples use placeholders; actual account-specific settings stay local.
Do not combine environment values and a tfvars file unintentionally: explicit
`-var-file` values take precedence over `TF_VAR_` values.

There is no Azure password, client secret or model API-key variable to populate.
Terraform authenticates through the signed-in Azure CLI. Local inference uses an
explicit Azure CLI credential and hosted inference will use managed identity.
Private keys, `.azure/` login caches, `.env` files, real `.tfvars`, Terraform
working directories, state/backups and saved plans are ignored by Git.

[sensitive does not encrypt or omit state/plan values](https://developer.hashicorp.com/terraform/language/manage-sensitive-data).
Saved plans/state can contain IDs, email and provider-generated credentials,
even with model key authentication disabled. Keep these local files private;
use owner-only permissions and encrypted storage for retained copies. Do not
publish `terraform show -json`, `terraform output -json` or raw outputs as
sanitized evidence: those commands can reveal sensitive values. `gitignore`
does not remove files that were already tracked. Check `git status` and the
staged diff before committing; this check does not rewrite repository history.

Generate a fresh plan after any configuration/input change. Use a restrictive
umask so binary plans, readable plan exports and future state are owner-only:

```sh
umask 077
terraform -chdir=infra/azure/model plan -var-file=private.tfvars -out=model.tfplan
terraform -chdir=infra/azure/model show -no-color model.tfplan > infra/azure/model/model.tfplan.txt
chmod 600 infra/azure/model/model.tfplan infra/azure/model/model.tfplan.txt
git check-ignore infra/azure/model/model.tfplan infra/azure/model/model.tfplan.txt
```

A readable plan still contains resource identifiers. The sensitive email is
redacted in the normal text view, but is still available to Azure's budget
service and is retained in the binary plan/state. Review that current private
plan before authorizing apply; older saved plans are superseded.

## Stages and approval gates

1. Confirm the cost guide, billing currency, budget recipient, model lifecycle,
   region, SKU and quota. The USD 5 amount is valid only for verified USD billing.
   Non-USD billing requires an explicit amount, exchange-rate date and recorded
   owner decision before changing Terraform's currency guard. A successful list
   response does not establish that a budget can be created for this offer.
2. Initialize and validate `infra/azure/model/`, then generate a fresh model-only
   plan using ignored local tfvars. Review its resources before applying it.
   This root owns the resource group, model account/deployment, developer role,
   and group budget; hosting is not included.
3. Verify the created budget's amount, currency, scope, actual 50/80/100 thresholds
   and recipient. Check the developer's account-scoped role. Poll read-only role
   state at most six times with ten seconds between attempts. Listing a role does
   not prove data-plane propagation. An inference failure must never trigger an
   automatic billable retry.
4. Only after approval, run a synthetic probe. It is **billable**, even if it
   returns no visible text. Use the deployed endpoint and selected tenant.
   The following direct CLI example deliberately acquires an Entra token through
   Azure CLI without printing it; do not enable debug tracing:

   ```sh
   cat > /private/tmp/azure-chat-probe.json <<'JSON'
   {"messages":[{"role":"system","content":"Answer concisely."},{"role":"user","content":"Hello"}],"max_completion_tokens":32,"reasoning_effort":"minimal","verbosity":"low"}
   JSON
   az rest --method post --resource 'https://cognitiveservices.azure.com/' \
     --url "${MODEL_ENDPOINT%/}/openai/deployments/$MODEL_DEPLOYMENT/chat/completions?api-version=2025-04-01-preview" \
     --body @/private/tmp/azure-chat-probe.json \
     --query '{text:choices[0].message.content,finish:choices[0].finish_reason,usage:usage}' -o json
   ```

   This CLI illustration is not the application's bounded-timeout probe; use the
   tested SDK probe when implemented. Before invoking either, check `az account
   show` matches the intended tenant/subscription. Empty, refusal, malformed usage,
   or reasoning-only output is a failed access test. A separate approved follow-up
   may deliberately use 512 tokens; never retry or increase tokens automatically.
   Record status/request ID, model/version/region/API, capacity, text and usage.
   Do not put credentials, real prompts or answers in operational evidence.
5. Leave hosting undeployed if the probe fails. For a successful probe, review the
   app-root identity bootstrap plan, test the image locally, explicitly publish
   the public GHCR image and verify its anonymous digest pull, then review a fresh
   `deploy_app=true` plan. Public images expose code/assets independently of source
   repository visibility. No registry passwords belong in Terraform or the image.
6. Verify actual Chrome login, owner-only queries, CSP/privacy, history behavior,
   managed identity, scale-to-zero and measured costs before checking live tasks.

Example model-only workflow (saved plans are private and single-use):

```sh
terraform -chdir=infra/azure/model init
terraform -chdir=infra/azure/model fmt -check
terraform -chdir=infra/azure/model validate
terraform -chdir=infra/azure/model test
terraform -chdir=infra/azure/model plan -var-file=private.tfvars -out=model.tfplan
terraform -chdir=infra/azure/model show model.tfplan
# Run only after reviewing and approving that exact current plan:
terraform -chdir=infra/azure/model apply model.tfplan
```

Do not apply a saved plan after changing inputs or following a partial apply:
preserve state and generate a new plan. Protect local state/backups and avoid
committing account-specific inputs. Independent local roots must not share a
state path. The app root must use the model root's RG and account outputs and own
its own cross-root runtime role assignment; do not recreate shared resources.

## Failure diagnosis and lifecycle

- Credential/tenant failure: sign into the selected tenant and recheck the active
  subscription. Never print tokens or use an API key fallback.
- Graph denied: fix directory app-registration/consent permissions; subscription
  Owner is not a substitute. Do not create a new tenant or move the subscription.
- Model access denied: verify the account-scoped OpenAI User role and bounded
  propagation checks, then inspect the safe category/status/request ID.
- Quota/capacity/model-version failure: compare the actual SKU/version/region
  with the cost guide; stop rather than silently changing the model or region.
- Empty/32-token reasoning-only response: access remains unproven. A deliberate
  normal-cap follow-up requires separate recorded authorization.
- Unsupported budget offer/currency: stop before billable inference. Choose a
  supported subscription or an explicitly agreed equivalent budget.
- Partial apply: retain state; diagnose the specific resource and re-plan.

Rollback uses a previously verified public immutable image digest and a fresh app
plan. Keep rollback digests available. On an explicit teardown request, first
review/destroy app resources and their runtime RBAC, then review/destroy model
resources including budget and dedicated group. Retain state until removal is
verified. Terraform does not remove GHCR packages; package/version cleanup is a
separate destructive request. Private AWS state/backups are retained in the Git-ignored
`infra/retained-aws-state/` directory. The historical AWS OpenSpec change and
obsolete local deployment files were removed at the owner’s explicit request.
Local file cleanup does not delete cloud resources.

See Microsoft's [budget tutorial](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets)
for offer support, permissions, delayed evaluation and notifications. Budgets are
alerts, not a spending cap. The application's token/rate/replica limits also do
not enforce a monthly dollar ceiling. GitHub usage is outside the Azure budget.

AWS-origin browser storage does not migrate to the new HTTPS origin. If needed,
access or clear it manually at its original origin; never reuse the Cognito
subject as an Azure owner object ID.

## Backend owner authentication

The backend Entra validator is implemented separately from live browser login.
See [the auth contract](azure-auth.md) for its required parameterized tenant/API/SPA/owner
settings, claim checks, cache behavior and remaining registration/browser work.

## Locked Python and shell examples

Use CPython 3.14.8 as pinned in `backend/.python-version`. From `backend/`, run
`pipenv verify` and `pipenv sync` (or `pipenv sync --dev` for tests). The retained
`bedrock_chat` import path avoids a mechanical package rename; the model and
examples now call Azure. The browser/auth/hosting migration is still a separate
set of tasks: these direct examples do not establish application readiness.

After an approved model apply, configure the **actual Terraform endpoint and
deployment outputs**, not example placeholders:

```sh
export AZURE_OPENAI_ENDPOINT='https://<actual-account>.openai.azure.com/'
export AZURE_OPENAI_DEPLOYMENT='gpt-5-mini'
export AZURE_OPENAI_API_VERSION='2025-04-01-preview'
export AZURE_TENANT_ID='<selected-directory-uuid>'
export AZURE_AUTH_MODE='azure_cli'
# Confirm that az account show reports the intended tenant/subscription first.
# Each following command makes one billable request; run only the approved one.
PYTHONPATH=src pipenv run python -m bedrock_chat.cli --tenant "$AZURE_TENANT_ID" --probe
# Shell wrapper for the same synthetic 32-token SDK probe:
PYTHONPATH=src pipenv run sh examples/query.sh --probe
# A separate deliberate 512-token request, only if approved:
PYTHONPATH=src pipenv run python -m bedrock_chat.cli --tenant "$AZURE_TENANT_ID" 'Hello'
```

Do not run all three as an automatic test sequence. The SDK examples have a
two-second connect timeout, fifteen-second request timeout, no inference retries,
low verbosity and minimal reasoning. Normal requests use 512 completion tokens;
`--probe` fixes the prompt to `Hello` and uses 32. A reasoning-only/refused/empty
response or malformed usage exits unsuccessfully; it never silently falls back
or raises the cap. Success prints only response text and normalized input/output
usage. Failure prints a fixed diagnostic without raw SDK exception text. Do not
set `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY` or `AZURE_OPENAI_AD_TOKEN`: the code
rejects these ambient credentials. Local credentials use Azure CLI with the
explicit tenant, not DefaultAzureCredential or an automatic fallback chain.

For later Container Apps runtime, use `AZURE_AUTH_MODE=managed_identity` and an
explicit user-assigned `AZURE_CLIENT_ID`. Hosted environments reject CLI mode.
The readiness route returns 503 for missing/invalid model settings; it performs
no billable inference. Actual authorization/inference remains a separate check.
