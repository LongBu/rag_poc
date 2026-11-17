# Staged Container Apps and Entra configuration

Implemented November 16, 2026; offline mocks are separate from live acceptance.

`infra/azure/app/` pins AzureRM 4.81.0 and AzureAD 3.10.0, with verified
macOS ARM64/Linux AMD64 dependency locks. Terraform 1.9+ is required for
cross-variable validation. The root has its own local state. It never reads
model state through `terraform_remote_state`, creates a resource group, changes
the budget, or owns the model account/deployment. Its only Azure resources are
the runtime user-assigned identity, account-scoped inference role and, on
activation, a Consumption environment and Container App. There is no registry,
gateway, database, retained logging workspace or subscription-wide runtime role.
The budget remains model-root-owned and covers the shared group.

Run these checks without cloud credentials:

```sh
terraform -chdir=infra/azure/app init -backend=false -lockfile=readonly
terraform -chdir=infra/azure/app fmt -check -recursive
terraform -chdir=infra/azure/app validate
terraform -chdir=infra/azure/app test
```

The 20 mock runs cover bootstrap without hosting, activated HTTPS/single
revision, 0.25 vCPU/0.5 GiB, zero-to-one replicas, probes, identity/RBAC,
public digest pulls without registry credentials, exact runtime settings,
Entra v2 delegated scope and generated callbacks, and rejected private inputs.
In the pinned AzureRM provider, `logs_destination = ""` means no retained
logging, with live streaming available. It is not the literal string `none`.
Readiness runs every five seconds with a two-second timeout; startup allows
30 failures at five-second intervals. Neither probe invokes inference.

## Model handoff and bootstrap

First confirm the successful model probe recorded in `azure-model-access.md`,
current costs, subscription/tenant selection and directory permissions from
`azure-setup.md`. Copy `terraform.tfvars.example` to an ignored private input
file with owner-only permissions. Copy the model root's public outputs for
`resource_group_name`, `location`, `model_account_id`, `model_endpoint`,
`model_deployment`, and `tenant_id`. Select the same subscription. The app root
validates the account's subscription/group and corresponding endpoint, deployment,
IDs, US region and immutable image syntax. Verify all copied outputs against the
selected model root before planning; mocks cannot prove the actual handoff.
`owner_object_id` is the user's immutable directory ID; the directory administrator
may be a different user and is recorded separately in `directory_admin_object_id`.
Never copy the model state or budget email into the image or source control.

With `deploy_app=false` (the default), bootstrap creates the managed identity,
model-account inference assignment, two Entra registrations/service principals,
application ownership, API identifier, delegated `query` scope, SPA permission
request and exact SPA preauthorization. It creates no hosting environment/app,
and no placeholder redirect URL. Bootstrap still changes the tenant and RBAC;
review its real plan before applying it.

```sh
terraform -chdir=infra/azure/app plan -var-file=/absolute/private/app.tfvars -out=bootstrap.tfplan
terraform -chdir=infra/azure/app show bootstrap.tfplan
# After review/approval only:
terraform -chdir=infra/azure/app apply bootstrap.tfplan
```

Saved plans contain private input values. Keep plans/state/backups private,
retain state after failures, and regenerate plans after input changes or partial
applies. Never reuse a consumed plan. Recheck that the plan contains the selected
subscription, tenant, group, account, owner and current stage values.

## Entra permissions and personal-account membership

Both registrations use `AzureADMyOrg`, access token version 2 and disabled
implicit grants. There are no application passwords or client secrets. The API
publishes `api://<API client ID>/query`; only the generated SPA client is
preauthorized for that delegated scope. This permits consent without granting
other users model access: Flask still checks tenant, audience, `query`, SPA client
and owner object ID. No Microsoft Graph application roles are granted to the
runtime. Scope UUIDs are deterministically derived from the API's generated ID.

Sign in to the selected tenant with the personal Microsoft account represented
as its existing member/guest identity. Verify `az ad signed-in-user show` and
`az account show` as described in setup. Do not select `common`/`consumers`, use
the personal account ID from another tenant, create a tenant, invite users, or
change subscription directory to work around a failure. Missing membership
requires the existing tenant administrator's assistance before deployment.
Subscription Owner does not grant directory app-registration/consent rights.

For `Authorization_RequestDenied`/insufficient privileges, identify whether the
failure is Graph application registration, application ownership, service
principal creation or scope preauthorization. The pinned provider documents
Application Administrator/Global Administrator for user-based preauthorization;
check the current tenant policy with the directory administrator. A provisioning
service principal needs the provider-documented Graph application permissions
and application ownership; subscription RBAC is a separate permission. A consent
failure needs directory policy/admin review, not an API secret or broader model
RBAC. Preserve state, resolve the specific permission, then generate a new plan.
Do not claim tenant sign-in or consent works until live acceptance passes.

## Activation without a callback cycle

After explicit publication and anonymous verification of the reviewed image,
set `deploy_app=true` and `image_digest=ghcr.io/<owner>/<image>@sha256:<64 hex>`
in the private app inputs. Generate a fresh activation plan and review costs and
resources before applying. Do not use a mutable tag or an authenticated registry.

The environment's generated default domain plus the app name gives the exact
HTTPS origin before container creation. This sets `FRONTEND_ORIGIN` and the
SPA logout URL without a self-reference to the Container App. A separate
`azuread_application_redirect_uris` resource registers the actual generated
app FQDN with type `SPA` after app creation. The registration itself never
depends on that redirect resource. A postcondition requires the app's actual
FQDN to match the configured origin. The exact root URL, including trailing
slash, is the sole callback and logout URL. Runtime config uses the generated
SPA/API client IDs and existing owner ID; every value is public, with no keys.

The runtime identity and its inference role precede container startup. RBAC can
still take time to propagate: use bounded read-only role/identity checks and
record a safe 503 if inference is not ready, without automatic model retries.
The UI can be reached briefly before callback registration finishes; wait for
the complete successful apply before login. An incomplete identity configuration
keeps queries denied. Outputs expose only public IDs/scope/URL, never credentials.

Sources checked against pinned provider docs:
[Container Apps environment](https://github.com/hashicorp/terraform-provider-azurerm/blob/v4.81.0/website/docs/r/container_app_environment.html.markdown),
[Container App](https://github.com/hashicorp/terraform-provider-azurerm/blob/v4.81.0/website/docs/r/container_app.html.markdown),
[application registration](https://github.com/hashicorp/terraform-provider-azuread/blob/v3.10.0/docs/resources/application_registration.md),
[preauthorization](https://github.com/hashicorp/terraform-provider-azuread/blob/v3.10.0/docs/resources/application_pre_authorized.md).

The owner-approved identity-only bootstrap has been applied: 12 creates, no
changes or destroys. Azure/Graph readback verifies the registrations, scope,
preauthorization, service principals, runtime identity and account-scoped role.
Hosting activation is now applied and its public routes/denied anonymous queries
are verified. The owner subsequently confirmed successful browser login and
a live answer through hosted inference; broader acceptance remains pending. The reviewed image is public and anonymously pullable.
See `azure-release.md` for the release and bootstrap evidence.
