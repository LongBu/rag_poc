# Personal Azure chat

Owner-only React/Flask chat using Azure OpenAI GPT-5 mini, Microsoft Entra sign-in
and one scale-to-zero Azure Container App. Flask serves the built frontend,
public runtime configuration and protected query API from the same HTTPS origin.
No retrieval, browsing, tools, model fallback or server-side conversation store.

Start with [Azure setup and permissions](docs/azure-setup.md) and
[the cost guide](docs/azure-costs.md). The USD 5 monthly budget sends alerts;
it does not stop spending. GitHub registry/build usage is outside that budget.
Implementation follows [the Azure OpenSpec tasks](openspec/changes/migrate-bedrock-chat-to-azure/tasks.md).
Unchecked tasks and unperformed live checks remain incomplete.

The Azure deployment was used for live browser and managed-identity inference
validation, then torn down on November 17, 2026. The GHCR package has since been
deleted by the owner; see [teardown evidence](docs/azure-validation.md). Task
6.4 was closed by [owner acceptance](docs/azure-operations.md#task-64-closed-by-owner-acceptance-november-17-2026)
of the below-USD-5 cost assumption; actual hosting-cost attribution, final Azure
reconciliation, final monthly GitHub coverage and budget email delivery remain
unverified. See [model access](docs/azure-model-access.md) and
[release evidence](docs/azure-release.md) for historical deployment details.

## Development setup

Use Git, standard CPython **3.14.8** (pinned in `backend/.python-version`),
Pipenv **2026.10.6**, Node **24** with bundled npm, Terraform **1.17.0** to match
CI (app root requires `>=1.9,<2.0`), and Docker with Linux/amd64 support.
Azure CLI is needed for live account/deployment work; offline tests need no
cloud credentials. Chrome is used for live browser acceptance.

On a new Mac, install Xcode Command Line Tools with `xcode-select --install`,
then install [Homebrew](https://brew.sh/) and follow its PATH setup instructions.
Install the tools and CPython build prerequisites:

```sh
brew install git pyenv node@24 azure-cli
brew install openssl@3 readline sqlite xz zlib tcl-tk@8 libb2 zstd pkgconf
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

Add Homebrew's `node@24/bin` to your shell PATH as its installer instructs.
Install and start [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/)
for your Mac architecture; `docker version` must show both Client and Server.
Linux development uses the same versions and a running Docker Engine supporting
Linux/amd64. Do not use macOS Python packages in the Linux image.

From the repository root, set up the locked backend environment:

```sh
cd backend
pyenv install -s 3.14.8
pyenv exec python -m pip install pipenv==2026.10.6
PIPENV_VENV_IN_PROJECT=1 pyenv exec pipenv sync --dev
pyenv exec pipenv verify
cd ..
npm --prefix frontend ci
```

`backend/` contains the Python app, examples and scripts; `frontend/` contains
React/Vite; `infra/azure/model/` and `infra/azure/app/` are separate Terraform
roots with separate state. Existing `bedrock_chat` imports and
`private-bedrock-chat` package metadata are retained to avoid a mechanical rename;
all active inference/auth/deployment paths use Azure.

Keep production and development dependencies separate. Commit Pipfile and its
lock together, and regenerate the lock only when changing dependencies. Keep
Terraform provider locks committed. Credentials, private inputs, state/backups,
plans, logs and build output stay outside version control and image layers.

## Offline checks

Run from the repository root:

```sh
(cd backend && pyenv exec pipenv verify && pyenv exec pipenv sync --dev)
(cd backend && pyenv exec pipenv run python -m pytest)
(cd backend && pyenv exec pipenv run python -c 'import json; r=json.load(open("coverage.json")); assert r["totals"]["missing_lines"] == r["totals"]["missing_branches"] == 0')
npm --prefix frontend ci
npm --prefix frontend run test:coverage -- --runInBand
node -e 'const r=require("./frontend/coverage/coverage-final.json"); for(const f of Object.values(r)) for(const k of ["s","f","b"]) for(const n of Object.values(f[k]).flat()) if(n===0) throw new Error("Uncovered application code")'
npm --prefix frontend run build
sh backend/scripts/build-container.sh
python3 backend/scripts/smoke-container.py
python3 backend/scripts/review-image.py --self-test
python3 backend/scripts/review-image.py
for root in infra/azure/model infra/azure/app; do
  terraform -chdir="$root" init -backend=false -lockfile=readonly
  terraform -chdir="$root" fmt -check -recursive
  terraform -chdir="$root" validate
  terraform -chdir="$root" test
done
```

Python statements/branches and frontend statements/branches/functions/lines must
be exactly 100% covered, including unimported application source. TypeScript
checking runs in `npm run build` before Vite. Unit tests mock model/auth network
boundaries. Terraform tests use mocked providers, with no apply to Azure.
Container smoke tests run actual Gunicorn HTTP in network-isolated non-root,
read-only containers with writable `/tmp` and synthetic auth/model services.
[Container details](docs/azure-container.md) describe the pinned bases and checks.
The image review scans every layer plus configuration/history before publication.

[GitHub Actions](.github/workflows/checks.yml) performs locked installs, these
coverage/build/container checks and both Terraform roots' format/validate/mock
tests. It has read-only repository permissions and no cloud credentials,
registry login, image publication or deployment action. Local success is
separate from an actual GitHub Actions run and live acceptance.

## Azure account, deployment and release

Follow these guides in order:

1. [Setup and permissions](docs/azure-setup.md): personal-account tenant membership,
   explicit subscription selection, separate directory/RBAC permissions, provider
   registration, quotas, billing currency and budget support.
2. [Model access](docs/azure-model-access.md): model-root bootstrap, budget and
   scoped developer inference role, then the separately authorized bounded probe.
3. [App infrastructure and Entra](docs/azure-app.md): validated model-output handoff,
   identity-only bootstrap, single-tenant v2 delegated query scope and exact SPA
   preauthorization. Use ignored owner-only private inputs.
4. [Public image release](docs/azure-release.md): review/test the exact image,
   publish explicitly to `ghcr.io/example/private-azure-chat`, verify anonymous
   pulling of its immutable digest, and retain rollback digests. Public images
   expose bundled code/assets independently of source-repository visibility.
5. Review a fresh activation plan with `deploy_app=true` and the verified public
   digest before applying. Container Apps uses managed identity, HTTPS ingress,
   Consumption 0.25 vCPU/0.5 GiB, min zero/max one replica, single revision,
   inference-free probes and live-only logging. No registry secret is needed.
6. Record actual owner login, managed-identity inference, security/privacy,
   browser behavior, cold-start/scaling and cost acceptance separately.

The model root owns the shared group/model/budget; the app root owns identity,
registrations, hosting and its model-account role. Preserve private state after
partial failure and create a fresh plan after any input change or partial apply.
Never reuse a consumed plan. Do not place publisher tokens, model API keys,
passwords or client secrets in Terraform or images. Entra tokens stay in browser
memory; the backend validates tenant, audience, scope, SPA client and owner ID.

## Direct CLI and SDK examples

After selecting the correct Azure account and verifying model-stage readiness,
use the actual endpoint/tenant outputs as described in
[setup](docs/azure-setup.md#locked-python-and-shell-examples). From `backend/`:

```sh
export AZURE_OPENAI_ENDPOINT='https://ACTUAL-ACCOUNT.openai.azure.com/'
export AZURE_OPENAI_DEPLOYMENT='gpt-5-mini'
export AZURE_OPENAI_API_VERSION='2025-04-01-preview'
export AZURE_TENANT_ID='ACTUAL-TENANT-UUID'
export AZURE_AUTH_MODE='azure_cli'
# Choose one deliberately authorized invocation; these are billable.
PYTHONPATH=src pyenv exec pipenv run python -m bedrock_chat.cli --tenant "$AZURE_TENANT_ID" 'Hello'
# Alternative shell wrapper for the same SDK, not an additional automatic check:
PYTHONPATH=src pyenv exec pipenv run sh examples/query.sh 'Hello'
```

The Python SDK entry point and shell wrapper use temporary Entra CLI credentials,
low verbosity/minimal reasoning, a 512 completion-token cap, bounded timeouts,
usage reporting and no automatic retries. `--probe` sends synthetic `Hello` with
32 completion tokens; reasoning-only output does not establish usable text and
does not trigger an automatic retry or larger budget. These examples bypass
browser login using the separate developer inference role. Hosted inference
uses the explicit user-assigned managed identity, with no CLI fallback.

For local frontend work, `npm --prefix frontend run dev` runs Vite; unit fixtures
supply fake public config/auth. Real login requires the registered exact HTTPS
origin. Do not disable owner authorization or weaken config validation for local
login. The built container provides the complete same-origin app. See the
[web contract](docs/azure-web.md), [frontend config](docs/azure-frontend-config.md),
[backend auth](docs/azure-auth.md) and [browser auth](docs/azure-browser-auth.md).
Missing model settings leave readiness unhealthy; missing identity settings deny
queries. Never enable debug mode or callback-bearing HTTP access logs.

## Conversation behavior and privacy

Submit or Enter sends once; Shift+Enter inserts a newline and IME composition
does not submit. Loading/error/usage feedback, draft preservation, copy-answer
feedback and scroll-position behavior are retained. Only the newest ten completed
pairs, bounded with the prompt to 32,000 code points, go to the model. Individual
prompts are capped at 4,000 code points and requests at 256 KiB. The server owns
the concise-answer instruction and generation parameters.

Browser history retains the newest 100 completed exchanges within 1 MiB UTF-8
JSON, separately from model context. Restore follows owner authentication and
is isolated by Azure tenant/owner object ID. Storage failure permits memory-only
use with a warning. Clear/logout, cross-tab locks and generation guards prevent
late responses from recreating erased history. Logout also removes in-memory
tokens and transient PKCE state; issued bearer tokens can remain valid until
expiry. Local history is not encrypted and can be read by someone with access
to the unlocked browser profile. See [history safeguards](docs/azure-history.md).

AWS-origin history is not imported or erased by this Azure app. Clear it manually
at its original origin if needed. Obsolete AWS deployment files and the historical AWS OpenSpec change were
removed at the owner’s request. Private AWS state/backups remain Git-ignored in
`infra/retained-aws-state/`; they are not active deployment instructions.

See [observed costs and operational procedures](docs/azure-operations.md) for
current billing evidence, rollback digests and reviewed teardown steps.

## Troubleshooting, rollback and teardown

Separate subscription access from directory registration/consent permissions.
Use tenant-specific personal-account membership and immutable object IDs, not
email addresses. Model access, quota/capacity, managed-identity propagation and
registration consent failures require their own diagnostics; do not broaden
runtime roles or add API keys as a workaround. Safe errors expose only bounded
categories/status/request IDs, never prompts, answers, credentials or raw provider
exceptions. See [admission limits](docs/azure-admission.md) for per-process
concurrency/rate controls and their restart/revision limitations.

Rollback uses a retained known-good public digest and a fresh reviewed app plan.
Teardown is only on request: review/destroy app resources and cross-root RBAC
before model resources/budget/group. Retain state until removal is verified.
Terraform teardown does not remove GHCR packages; package/version cleanup needs
a separate request and must preserve deployed/rollback digests. Budget alerts,
replica limits and trial credits are not a monthly spending cap.
