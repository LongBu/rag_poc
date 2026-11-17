# Explicit public image release

> Privacy: account names, application origins, image digests and request IDs in this document are synthetic placeholders; replace them before use.

Updated November 16, 2026. The owner published the reviewed image and made
it public. The approved identity bootstrap and hosting activation have now been applied.
Owner browser login and managed-identity inference acceptance remain pending.
Use [the app-stage guide](azure-app.md) for model handoff, directory permissions,
bootstrap, generated callbacks and reviewed Terraform plans.

## Local review evidence

The existing Linux/amd64 application image was inspected with
`python3 backend/scripts/review-image.py`; its nine layers, 13,417 regular files,
runtime environment and untruncated build history passed. Local image ID:
`sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb`.
This is a local configuration ID, **not** a GHCR deployment manifest digest.
The image previously passed the task 4.3 HTTP smoke checks (`azure-container.md`).
No application runtime source changed during tasks 4.4/4.5.

The scanner reviews every layer, including files later deleted. It rejects
private cloud/Git/env/Terraform paths, unexpected files under `/app`, high-confidence
private-key/token markers and unexpected runtime environment keys. It allows
only package Python source, Gunicorn config, built HTML and hashed JS/CSS under
`/app`; logs, chat data, state and private config cannot be added there. The
Dockerfile/build-context allowlist supplies only intended manifests/source.
The checked history contains pinned public bases, locked package installs and
copies, with no publisher login, private input, state or credential mount.
The self-check verifies rejected private files/secrets and the benign crypto
parser delimiter that initially triggered the scan. These are focused checks,
not a guarantee that every possible secret encoding is recognizable. Do not
add private values to source, build arguments, dependencies or layers and rely
on a final-layer deletion to hide them.

Rerun review on the **exact** image before each publication:

```sh
sh backend/scripts/build-container.sh
python3 backend/scripts/smoke-container.py
python3 backend/scripts/review-image.py --self-test
python3 backend/scripts/review-image.py
```

## Publisher identity and public visibility

Choose the target `ghcr.io/<account-or-organization>/<image>` explicitly.
A public image exposes all bundled source/assets/dependencies independently of
repository visibility. First pushes default to private: use the package's GitHub
settings to explicitly change package visibility to Public, and review any
inherited repository permissions. Keep source-repository visibility as intended.
Anyone may download public layers; Entra/Flask authorization protects inference,
not the image contents. CI performs no login, push or deployment.

GitHub's [registry documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
was rechecked on this date: public pulls support anonymous access; manual pushes
use a classic PAT with `write:packages` and any required organization SSO. Keep
the publisher credential separate from any cleanup credential; do not grant
`delete:packages` to the routine publisher token. Keep credentials outside
Terraform, source, shell tracing, build arguments, images and runtime.
Use an isolated temporary Docker config for publication, a secret prompt and
`--password-stdin`, then remove that temporary credential config securely.
Do not paste a literal token into commands or a saved plan.

After approval of the exact target and reviewed image, the manual release uses
these commands (replace placeholders; they have not been executed):

```sh
GHCR_IMAGE=ghcr.io/ACCOUNT/IMAGE
GHCR_TAG=reviewed-2026-11-16
PUBLISH_CONFIG=$(mktemp -d)
# zsh: read the PAT without terminal echo or a literal value in history.
read -r -s 'GHCR_PAT?GitHub package publisher token: '
printf '\n'
printf '%s' "$GHCR_PAT" | docker --config "$PUBLISH_CONFIG" login ghcr.io -u ACCOUNT --password-stdin
unset GHCR_PAT
docker tag private-azure-chat:local "$GHCR_IMAGE:$GHCR_TAG"
docker --config "$PUBLISH_CONFIG" push "$GHCR_IMAGE:$GHCR_TAG"
# Change the package visibility to Public in GitHub package settings.
# Record the push's sha256 manifest digest, not the local image ID.
docker --config "$PUBLISH_CONFIG" logout ghcr.io
```

Do not publish a newly rebuilt image without reviewing/testing that image.
Do not infer anonymous access from a successful authenticated push or from a
cached image. Use a separate empty Docker config to explicitly pull the exact
remote manifest digest without registry credentials:

```sh
ANONYMOUS_CONFIG=$(mktemp -d)
DEPLOY_IMAGE=ghcr.io/ACCOUNT/IMAGE@sha256:REPLACE_WITH_PUSH_MANIFEST_DIGEST
DOCKER_ENDPOINT=$(docker context inspect --format '{{.Endpoints.docker.Host}}')
docker --host "$DOCKER_ENDPOINT" --config "$ANONYMOUS_CONFIG" pull --platform linux/amd64 "$DEPLOY_IMAGE"
docker image inspect "$DEPLOY_IMAGE" --format '{{.Id}} {{.Architecture}} {{json .RepoDigests}}'
python3 backend/scripts/review-image.py "$DEPLOY_IMAGE"
```

Verify the pulled image ID equals the reviewed local ID and architecture is
amd64. Record the immutable public digest and successful anonymous pull before
activation. Remove the temporary config directories after all operations,
including errors. Never reuse the publisher config as proof of anonymous access.
Do not grant Azure a registry credential or create an Azure Container Registry.

## Costs, plans, rollback and teardown

GitHub's [billing policy](https://docs.github.com/en/billing/concepts/product-billing/github-packages)
was rechecked November 16, 2026: container storage/bandwidth are currently free,
with advance notice promised for changes. Publisher/Actions/runner/artifact costs
remain separate and unverified for this publisher. Those charges are outside the
Azure resource-group budget. The [Azure cost guide](azure-costs.md) distinguishes
gross charges, shared recurring allowances and zero assumed promotional credits.
Recheck all prices, allowances and the publisher's plan before hosting apply.

After the verified model handoff and reviewed bootstrap, save current app
inputs with `deploy_app=true` and the exact anonymous digest. Generate a fresh
activation plan; confirm group, tenant, owner, generated clients, managed
identity/account-scoped inference role, digest and HTTPS origin match. Review
resource counts and the budget/idle-cost assumptions before applying. Keep all
shared resources/budget model-root-owned and the runtime role app-root-owned.
Never reuse a bootstrap plan for activation or an old plan after any input change.

Retain the previous known-good public digest and state for rollback. A rollback
sets the previous digest in private inputs, reviews a new app plan and applies
it after approval. Single revision/one replica do not eliminate overlap or
spending; local admission controls are per process. Verify runtime managed-identity
inference and real owner login after activation; mock success does not prove RBAC
propagation, consent, cold-start timing or actual cost visibility.

Destruction requires a separate request and reviewed destroy plans. Remove the
app root (hosting, callback configuration, registrations, identity and cross-root
role) before the model root (model, account, budget and resource group). Preserve
state/backups until actual removal is verified. Azure teardown leaves GHCR
packages untouched; package/version deletion is separately requested and must
preserve deployed/rollback digests until explicitly retired.

### Deleting the GHCR package

Package deletion is separate from Terraform. The simplest option is to open the
package on GitHub, select **Package settings**, then choose **Delete this package**.
For command-line/API cleanup, authenticate `gh` as the package owner with a
**classic personal access token** that has both `read:packages` and
`delete:packages` (and authorize it for organization SSO if required). The
attempted authenticated-user endpoint was:

```sh
gh api --method DELETE user/packages/container/private-azure-chat
```

GitHub returned HTTP 403, `You need at least delete:packages and read:packages
scopes to delete a package`, when the active CLI token lacked these scopes. A
fine-grained token without the required package scopes will not work for this
endpoint. A separate cleanup token is optional: a user may instead use the GitHub
package settings page. If using a token, keep it short-lived and out of Terraform
variables, state, repository secrets and the Docker publisher config. Confirm the
package owner/name before deletion because package deletion removes its published
tags and rollback images.

## Verified public release

The owner published `ghcr.io/example/private-azure-chat:reviewed-2026-11-16`
and made the package public. Independent Docker pulls of both that tag and
its exact immutable digest succeeded with a fresh empty Docker credential
configuration. The existing Docker Desktop daemon endpoint was passed explicitly
because an empty config otherwise loses the desktop context and selects a
nonexistent default Linux socket. No publisher token was read or forwarded.

Verified deployment reference:

```text
ghcr.io/example/private-azure-chat@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```

## Teardown

The Azure deployment was removed on November 17, 2026; see
[`azure-validation.md`](azure-validation.md). The owner subsequently deleted the
GHCR package through GitHub package settings after the API request was rejected
for missing `delete:packages` and `read:packages`. The Azure app and package are
no longer available for rollback. The cleanup endpoint, required classic PAT
scopes and observed 403 are documented above for future teardown. Task 6.4 cost
reconciliation is still incomplete.

The registry-reported digest equals the local image ID in this particular
publication; that equality was observed rather than assumed. The pulled image
is Linux/amd64 and matches the previously reviewed image. Repeating the layer,
metadata and history review on this exact reference passed: nine layers and
13,417 files. The temporary anonymous Docker configurations were removed.
No GitHub package settings were changed by the agent.

The selected Azure CLI subscription/tenant were verified against model outputs,
and the signed-in directory object ID was read successfully. Owner-only ignored
`infra/azure/app/private.tfvars.json` now contains the actual model handoff,
owner/directory administrator and public digest, with `deploy_app=false`.
A fresh `bootstrap.tfplan` and owner-only text export were generated. All saved
plan input values were programmatically compared to current private inputs.
The plan proposes exactly 12 creates: two registrations, two application owners,
two service principals, API identifier/scope, SPA API access/preauthorization,
one runtime managed identity and its account-scoped inference assignment.
There are no changes, destroys, hosting, model, budget or resource-group creates.
All private inputs/plan exports are confirmed Git-ignored. This bootstrap plan
was subsequently applied after explicit owner approval; see the readback below.

Task 4.6 remains incomplete: real managed-identity access is still pending.
Task 6 acceptance, including browser/security/cost checks, remains unchecked.

## Approved identity bootstrap applied

On November 16, 2026, the owner explicitly authorized applying the saved
bootstrap plan. Immediately before apply, every saved input was compared with
the current private input file; the resource addresses/actions were confirmed
as the approved 12 creates, with `deploy_app=false`. Terraform applied
successfully: 12 added, zero changed, zero destroyed. The consumed
`bootstrap.tfplan` must not be reused. Private state and the apply log remain
local and Git-ignored.

Independent Azure/Graph readback verified both single-tenant v2 applications,
enabled service principals, disabled implicit grants, no application keys or
passwords, the sole delegated `query` scope, exact SPA preauthorization and
required API access. The runtime user-assigned identity matches the selected
tenant, and its Cognitive Services OpenAI User assignment exists at the exact
model-account scope. Bootstrap contains no placeholder redirect/logout URL,
Container App or environment. Real inference by that managed identity remains
unverified; creating/readback of RBAC is not proof of data-plane propagation.
No model invocation, hosting activation, package modification or deletion was
performed during this bootstrap. Task 6.1 is only partially satisfied and stays
unchecked, as do browser/security/cost acceptance and task 4.6's live
managed-identity verification.

The post-apply read-only Terraform plan returned exit code 0 with no changes.

## Approved hosting activation applied

After explicit owner approval, saved activation inputs and resource actions
were rechecked immediately before applying the reviewed plan. Apply succeeded:
three added, one changed, zero destroyed. Environment creation took 13 minutes
25 seconds, the app 18 seconds, and the redirect resource one second. The
consumed activation plan must not be reused. Canonical private inputs now retain
`deploy_app=true` and the deployed public image digest, matching activation
inputs. Private state, plans and logs are retained and Git-ignored.

Site: https://chat.example.invalid

Azure readback verifies successful provisioning, the exact published image
digest, user-assigned identity, HTTPS-only ingress and no registry credentials.
Entra readback verifies the sole exact HTTPS root callback and logout URL. Live
GETs to `/ready`, `/`, `/config.json` return 200; public config matches the
selected tenant/API/SPA/owner/scope/origin contract. Anonymous and forged-token
query POSTs return 401. Delivered no-referrer was checked on those responses.
A fresh post-activation Terraform plan reports no changes.

A console-based 32-token managed-identity probe could not start because Azure's
console service returned Service Unavailable (HTTP 503). No completed remote
model invocation was observed. One subsequent console connectivity check using
`python --version` also failed, without requesting inference. This management
console failure does not establish a model or application failure. The owner
was asked to verify Chrome sign-in and one synthetic Hello through the real
site. Browser/managed-identity acceptance is still pending, so tasks 4.6 and
6.1 remain unchecked. Full task 6.2/6.3/6.4 acceptance remains unperformed.

## Owner browser acceptance for task 6.1

After hosting activation, the owner reported successful use of the live site:
sent `Hello.` and received `Hi — how can I help you today?` in the Assistant
response, with the Copy answer control visible. This is user-reported Chrome/
browser acceptance, not an agent-operated browser trace. Together with verified
deployed identity settings, owner-only backend authorization, exact callback/
logout registration and managed-identity-only runtime configuration, the live
answer establishes the owner login and hosted inference path for task 6.1.
The earlier unavailable management-console probe remains recorded as failed
to start; it was not retried as a model invocation or claimed successful.

Tasks 4.6 and 6.1 are now complete. Exact token usage was not supplied in the
owner's report and no request ID or timing is invented. Full follow-up/history/
clear/logout/cross-tab/keyboard/scroll, adversarial-token, enforced CSP/log
privacy, scaling/latency and actual-cost acceptance remain tasks 6.2–6.4.

## Private Azure chat name release

The owner authorized publishing/deploying the visible name change. The app
heading and HTML title now say `Private Azure chat`. All 169 frontend tests
pass at exact 100% coverage; strict TypeScript/Vite, Linux/amd64 build, actual
container HTTP smoke and all-layer/history review pass (nine layers/13,417 files).
The tested image was published as `ghcr.io/example/private-azure-chat:azure-name-20261117-023716`
and pulled anonymously by its exact immutable digest:

```text
ghcr.io/example/private-azure-chat@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

The reviewed saved plan contained only one Container App image update.
Apply succeeded: zero added, one changed, zero destroyed. Canonical private
inputs retain the deployed digest. Live HTML title and served JavaScript
contain `Private Azure chat` and no old visible name; readiness returns 200,
anonymous query returns 401, and Azure readback confirms the exact image.
A post-update Terraform plan reports no changes. No inference was performed
for this cosmetic release. The previous public digest remains for rollback:

```text
ghcr.io/example/private-azure-chat@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```

## Task 6.4 closeout

On November 17, 2026, the owner accepted the below-USD-5 cost assumption based
on small usage and closed task 6.4 with the remaining billing checks explicitly
unverified. This supersedes earlier incomplete-status notes; see
[the acceptance record](azure-operations.md#task-64-closed-by-owner-acceptance-november-17-2026).
