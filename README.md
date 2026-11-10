# Personal Bedrock chat

Read the [cost guide](docs/bedrock-costs.md) before deploying. The $5 budget is
an alert, not a spending cap. Implementation follows the
[OpenSpec tasks](openspec/changes/add-budget-bedrock-access/tasks.md); unchecked
tasks are not yet verified or ready to deploy.

## Development prerequisites

The Python application, tests, Lambda packaging, examples, and build scripts
live in `backend/`. The browser application lives in `frontend/`, and Terraform
lives in `infra/bedrock/`. Frontend and Terraform commands below run from the
repository root unless specified otherwise.

### Fresh macOS machine setup

Install these tools before running the project. This walkthrough targets macOS
with zsh, on Apple Silicon or Intel. Linux users need the same tool versions,
their distribution's Python build dependencies, and a running Docker Engine
with `linux/amd64` support; the Homebrew/macOS commands are not Linux setup steps.

| Tool | Project requirement | Purpose |
| --- | --- | --- |
| Xcode Command Line Tools | Supported by your macOS version | Compiler and SDK for building CPython |
| Homebrew and Git | Current supported releases | Install tools and obtain the repository |
| pyenv | Current release supporting the pinned Python | Select standard CPython without changing system Python |
| CPython | `backend/.python-version` (currently 3.14.8) | Backend development, tests, SDK examples |
| Pipenv | 2026.10.6 | Install the locked backend dependencies |
| Node.js and bundled npm | Node 24 matches CI | Frontend dependencies, tests, build |
| Docker Desktop | Supported macOS release; running engine | Linux Lambda ZIP build and adapter smoke tests |
| Terraform | `>=1.7,<2.0`; CI uses 1.17.0 | Infrastructure validation, planning, deployment |
| AWS CLI | v2 | Account checks, owner bootstrap, frontend upload |
| Chrome | Current supported release | Live browser acceptance checks |

1. Install Apple's compiler tools, complete the installer, then verify them:

   ```sh
   xcode-select --install
   xcode-select -p
   ```

   If the tools are already installed, skip the installation command.

2. Install [Homebrew](https://brew.sh/) using its official installer:

   ```sh
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

   Follow the installer's **Next steps** to add Homebrew to `~/.zprofile` and
   initialize the current terminal. The standard prefixes are `/opt/homebrew`
   on Apple Silicon and `/usr/local` on Intel. Confirm `brew --version` works
   before continuing, including in a newly opened terminal.

3. Install command-line tools and CPython build libraries:

   ```sh
   brew install git pyenv node@24 awscli
   brew install openssl@3 readline sqlite xz zlib tcl-tk@8 libb2 zstd pkgconf
   brew tap hashicorp/tap
   brew install hashicorp/tap/terraform
   ```

   See pyenv's [build environment guidance](https://github.com/pyenv/pyenv/wiki#suggested-build-environment)
   if Python compilation fails. Homebrew's Node 24 formula needs its own PATH
   entry. Add it once to your zsh startup file and activate it now:

   ```sh
   echo 'export PATH="$(brew --prefix node@24)/bin:$PATH"' >> ~/.zprofile
   export PATH="$(brew --prefix node@24)/bin:$PATH"
   node --version
   npm --version
   ```

   npm comes with Node; do not install it separately. Homebrew's Terraform
   release can be newer than CI; verify it remains in the supported 1.x range.
   For the exact CI version, use the matching binary from
   [HashiCorp's official releases](https://releases.hashicorp.com/terraform/1.17.0/).
   Tools such as AWS CLI may install their own Python dependencies; the project
   interpreter is still the CPython version selected by pyenv below.

4. Install [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/),
   choosing Apple Silicon or Intel for your machine. Move Docker to Applications,
   open it, complete its first-run setup (including CLI access), and wait for the
   engine to start. Merely installing the `docker` CLI is not enough. Verify:

   ```sh
   docker version
   docker info
   docker run --rm --platform linux/amd64 alpine:3.22 uname -m
   ```

   `docker version` must show both Client and Server. The final command should
   print `x86_64`; it verifies the Lambda target architecture on either Mac type.
   It downloads a small test image and makes no AWS calls. Install
   [Chrome](https://www.google.com/chrome/) for the deployed browser checks.

5. Obtain the repository and open a terminal at its root. Run the backend setup
   immediately below (it returns to the root), then install frontend dependencies:

   ```sh
   npm --prefix frontend ci
   git --version
   pyenv --version
   node --version
   npm --version
   terraform version
   aws --version
   ```

   Use the checked-in lock files; no global React, TypeScript, Jest, Gunicorn,
   Flask, or LangChain installation is needed. Run the backend tests below,
   `npm --prefix frontend run test:coverage -- --runInBand`, and
   `npm --prefix frontend run build`. Then follow **Lambda ZIP and adapter checks**
   and **Read-only account preflight** before creating a deployment plan.
   Installing AWS CLI does not supply credentials or grant IAM permissions;
   authentication and Terraform deployment inputs are separate setup steps.

### Backend environment

Use standard **CPython 3.14** for local code, CI, Lambda, and SDK examples.
The local patch version is pinned in `backend/.python-version`. With pyenv installed:

```sh
cd backend
pyenv install -s 3.14.8
pyenv exec python -m pip install pipenv==2026.10.6
PIPENV_VENV_IN_PROJECT=1 pyenv exec pipenv sync --dev
pyenv exec pipenv run python --version
cd ..
```

Pyenv initialization in your shell is optional when using `pyenv exec`. This
project does not change your global Python version. Pipenv manages the backend
virtualenv in `backend/.venv`; recreate it after changing Python versions.
`backend/Pipfile` declares direct runtime/development dependencies and
`backend/Pipfile.lock` records resolved versions and hashes. Commit both.
Run `pyenv exec pipenv lock` in `backend/` only when changing dependencies,
and use `pyenv exec pipenv verify` plus `sync --dev` for existing locks. The macOS interpreter is for development;
Lambda dependencies must be built for Amazon Linux 2023 and the selected Linux
architecture, including native wheels. Do not deploy macOS site-packages.

Run the backend's offline unit tests from the repository root; this block enters
`backend/` and returns afterward:

```sh
cd backend
pyenv exec pipenv verify
pyenv exec pipenv run pytest --cov=src --cov-branch --cov-fail-under=100
pyenv exec pipenv run python -c 'import json; r=json.load(open("coverage.json")); assert r["totals"]["missing_lines"] == r["totals"]["missing_branches"] == 0'
cd ..
```

Coverage includes every Python source module under `backend/src`, imported or not,
with terminal, XML, and JSON reports. Tests mock AWS and JWKS requests; no model
invocation is needed. The exact missing-counter check prevents rounding from
hiding uncovered lines or branches. Run Gunicorn locally with
`PYTHONPATH=src pyenv exec pipenv run gunicorn 'bedrock_chat.app:create_app()'`; without the
issuer, client ID, and owner subject it serves readiness but rejects queries.
Do not enable Flask debug mode or HTTP access logs containing request bodies,
Authorization headers, or OAuth query parameters.

Infrastructure development requires Terraform 1.7 or later in the 1.x series
(mock provider tests require 1.7+), a current AWS CLI v2, and authenticated AWS
SSO or another temporary-credential profile. Frontend builds require Node.js
22.12+ and npm. Linux packaging/smoke tests require Docker with support for the
Lambda target architecture. Dependency lock files belong in version control;
state, credentials, private variables, build output, and saved plans do not.

## Lambda ZIP and adapter checks

With Docker Desktop running, build and test from the repository root:

```sh
sh backend/scripts/build-lambda.sh
(cd backend && pyenv exec python scripts/smoke-lambda.py)
```

The build verifies the Pipfile lock, exports production-only pinned dependencies
with hashes to a temporary container file, and installs them with pip hash
verification. No requirements files are maintained in the repository, and
Pipenv/development dependencies are excluded from the ZIP.

The build uses digest-pinned AWS Python 3.14/Amazon Linux 2023 and Web Adapter
1.1.0 images targeting `linux/amd64`, matching Lambda `x86_64`. Native wheels
are installed inside Linux; source, dependency metadata/licenses, and executable
`run.sh` are zipped into ignored `backend/artifacts/lambda.zip`. The script checks ZIP
integrity, native imports, architecture, CPython version, disabled Flask debug,
and expanded size including the adapter against Lambda's 250-MiB limit.

The build reports compressed and expanded ZIP sizes and enforces the expanded
size limit. The dependency bundle needs a private S3 artifact bucket rather
than direct upload; Terraform reads `backend/artifacts/lambda.zip`.
The local image is a build/test tool; deployment remains ZIP-based with no
registry requirement. Runtime Terraform must attach pinned
`arn:aws:lambda:us-east-1:753240598075:layer:LambdaAdapterLayerX86:30`, set
`AWS_LAMBDA_EXEC_WRAPPER=/opt/bootstrap`, handler `run.sh`, and the adapter's
port/readiness environment shown in `backend/lambda/Dockerfile`. Web Adapter is licensed
under Apache-2.0; its [versioned wrapper source](https://github.com/aws/aws-lambda-web-adapter/blob/v1.1.0/layer/bootstrap)
is reproduced only in the local layer fixture, not the application ZIP. Review
the published layer version/architecture/license before actual deployment.

Smoke tests invoke the real adapter through the Lambda Runtime Interface
Emulator and verify readiness, HTTP API v2 conversion, headers, base64/JSON
bodies, success/status/error handling, rejected auth, and OPTIONS. Synthetic
authentication and model responses are injected only from a test-only mount;
the build/ZIP contains no fake authentication or model. No host AWS credentials
are mounted or forwarded. Gunicorn access logs are disabled and provider error
details are suppressed. These checks do not establish live Cognito/Bedrock
access, actual Lambda latency, or deployed browser behavior.

After the ZIP exists, run infrastructure checks from the repository root:

```sh
terraform -chdir=infra/bedrock init -backend=false -lockfile=readonly
terraform -chdir=infra/bedrock fmt -check -recursive
terraform -chdir=infra/bedrock validate
terraform -chdir=infra/bedrock test
```

Initialization downloads the provider; these tests use mock AWS providers and
do not deploy resources. Continue with real account authentication and the
preflight below before planning a deployment.

When updating providers, run `terraform -chdir=infra/bedrock providers lock -platform=darwin_arm64 -platform=linux_amd64`
and commit the lock file so both local macOS and Linux CI checksums are recorded.

## Read-only account preflight

Choose an existing temporary-credential profile. Do not paste credentials into
source or shell scripts. Run `aws sso login --profile PROFILE` separately when
the profile needs renewed authentication. These inspections do not invoke a
model or deploy resources:

On macOS, install the AWS CLI if `aws` is unavailable: `brew install awscli`.
Verify installation with `aws --version`. Installation does not authenticate it.

```sh
aws sts get-caller-identity --profile PROFILE --no-cli-pager
aws bedrock get-foundation-model --profile PROFILE --region us-east-1 \
  --model-identifier amazon.nova-micro-v1:0 --no-cli-pager
aws bedrock get-foundation-model-availability --profile PROFILE --region us-east-1 \
  --model-id amazon.nova-micro-v1:0 --no-cli-pager
```

Review the account, principal, model lifecycle, text output support, `ON_DEMAND`
inference support, regional availability, and authorization/agreement/entitlement
status. If any check fails, stop before deployment; do not silently switch model,
region, or inference profile. Check current prices and credits as described in
the cost guide. Command flags were checked against AWS CLI documentation;
account results still require a configured CLI and account access.

Check Lambda concurrency capacity and the pinned adapter layer too (omit
`--profile PROFILE` when using environment credentials):

```sh
aws lambda get-account-settings --profile PROFILE --region us-east-1 \
  --query AccountLimit --no-cli-pager
aws lambda get-layer-version --profile PROFILE --region us-east-1 \
  --layer-name arn:aws:lambda:us-east-1:753240598075:layer:LambdaAdapterLayerX86 \
  --version-number 30 --no-cli-pager
```

The function reserves one concurrent invocation. Confirm the account can reserve
it before applying. If these reads return AccessDenied, ask an IAM administrator
to grant the permissions in [the preflight policy](docs/iam/bedrock-preflight.json).
That policy covers inspections; deployment needs the additional permissions below.

Deployment inputs are a stable same-account IAM user/role ARN (not an expiring
STS assumed-role session ARN), budget email, unique resource-name prefix, and
later the owner's immutable Cognito subject. SSO callers need their underlying
IAM role ARN. The caller must independently have `sts:AssumeRole` for the CLI
role; trusting a principal does not itself grant that caller permission.

The deploying principal needs scoped resource lifecycle/read permissions for
IAM roles/policies and PassRole, Bedrock model inspections, Budgets,
Lambda/layers, API Gateway v2, Cognito user pools/clients/domains/resource
servers, S3 buckets/objects/policies, CloudFront distributions/OAC/headers, and
CloudWatch log groups. Owner bootstrap additionally needs Cognito
AdminCreateUser/AdminGetUser. Billing Credits/Free Tier views require billing
access. Model runtime roles do not need these deployment or billing permissions.

## Deployment and owner bootstrap

Use the [cost guide](docs/bedrock-costs.md) first. Supply the identifying inputs
through Terraform's native environment variables in the terminal that will run
Terraform. These Bash/zsh prompts keep the entered values out of shell history
and disable input echo:

```sh
printf 'Trusted IAM user/role ARN: '
read -r -s TF_VAR_trusted_principal_arn
printf '\nBudget alert email: '
read -r -s TF_VAR_budget_email
printf '\n'
export TF_VAR_trusted_principal_arn TF_VAR_budget_email
```

Terraform reads those environment variables as `trusted_principal_arn` and
`budget_email`; the existing validation still applies. Both variables are
marked sensitive to redact normal plan/apply output. No file containing your
actual ARN or email is needed. No `terraform.tfvars` file is required. Supply
other settings with `-var` arguments, as shown below, or `TF_VAR_*` environment
variables. An ignored tfvars file remains optional; its values override
environment variables, and explicit `-var` arguments override both. Keep the
ARN/email in environment variables rather than literal command arguments that
would enter shell history.

Environment variables and `sensitive` do not anonymize deployment or encrypt
values. Terraform saved plans, JSON output, and state can contain the supplied
values, and AWS IAM/Budgets configuration and audit logs retain identifiers.
Protect state and any newly generated plan; do not print the environment or
save Terraform JSON output to shared logs. The obsolete local saved plan was
removed because it retained the previous file-based inputs.

Existing AWS
environment credentials work too; omit `--profile PROFILE` in the CLI examples
when using the environment credential chain. Never echo or commit credential
values. Confirm `get-caller-identity` matches the intended account and principal.

After local tests/build and read-only account checks pass, prepare a plan:

```sh
terraform -chdir=infra/bedrock init -lockfile=readonly
terraform -chdir=infra/bedrock plan \
  -var='owner_sub=' \
  -var='monthly_budget_usd=5' \
  -out=deployment.tfplan
terraform -chdir=infra/bedrock show deployment.tfplan
```

Run these commands from the project root. After reviewing and approving the plan:

```sh
terraform -chdir=infra/bedrock apply deployment.tfplan
```

The saved plan contains the input values; do not repeat `-var` arguments during
this apply. Preserve any non-default settings on subsequent plan commands.

Review the concrete resources, account, model, cost assumptions, and permissions
before an authorized apply of that saved plan. Unset environment variables only
after the commands that need them have finished. The initial empty `owner_sub`
denies all queries. The private artifact bucket holds the oversized ZIP;
Terraform manages its hash-named object and replaces/removes old managed
objects on code updates. No bucket versioning is enabled. Keep artifacts and
frontend storage private. Keep CloudFront access logging disabled because its
standard format captures callback query parameters. API logs contain only
request ID, status, and latency, with seven-day retention. Flask handles CORS
for the exact frontend origin; the unauthenticated OPTIONS route makes no model
or authentication calls. POST always requires both API JWT authorization and
independent backend owner validation. CORS does not authorize queries.

The budget's seven service labels must be checked against the target account's
billing dimensions before apply. Budget filters aggregate unrelated usage of
those services too; notifications are delayed and never stop spending. Verify
actual public prices, available credits separately, Lambda layer metadata, and
the account's reserved-concurrency quota. A concurrency of one may need a quota
increase if the account cannot reserve any function concurrency.

After authorized infrastructure deployment, build and upload the frontend:

```sh
npm --prefix frontend ci
npm --prefix frontend run build
terraform -chdir=infra/bedrock output -json frontend_config > frontend/dist/config.json
aws s3 sync frontend/dist/ s3://FRONTEND_BUCKET/ --exclude index.html --exclude config.json --cache-control 'public,max-age=31536000,immutable'
aws s3 cp frontend/dist/index.html s3://FRONTEND_BUCKET/index.html --content-type text/html --cache-control no-cache
aws s3 cp frontend/dist/config.json s3://FRONTEND_BUCKET/config.json --content-type application/json --cache-control no-store
```

Replace `FRONTEND_BUCKET` with the exact `frontend_bucket` output. Uploads do
not delete old assets; review and remove obsolete objects separately if needed.
The config contains public API/Cognito identifiers, including the owner subject,
and no secret. Regenerate/upload it after setting `owner_sub`. CloudFront uses
the generated HTTPS distribution domain and root callback URL. Do not use the
S3 website endpoint or make buckets public. The production CSP permits bundled
same-origin scripts and the exact API/Cognito endpoints; there are no analytics,
third-party scripts, inline executable scripts, or HTML injection.

The infrastructure outputs `account_id`, `region`, `model_id`, `cli_role_arn`,
`frontend_url`, `frontend_bucket`, `user_pool_id`, `client_id`, `issuer`, and
`login_origin`. The static frontend shell and public OAuth configuration are
downloadable without sign-in; private messages and model queries require login.
S3 is private and only CloudFront's signed origin requests can read its objects.
Do not deploy until the remaining OpenSpec implementation checks pass.
The required lifecycle is build/tests → read-only preflight → saved Terraform
plan review → authorized apply.

Your AWS IAM identity deploys the infrastructure; your Cognito user signs into
the website. These are separate identities. `TF_VAR_owner_sub` supplies
Terraform's `owner_sub` input: the permanent Cognito user ID (`sub`), not your
email, password, or IAM ARN. Two deployments are needed because the Cognito
pool and user must exist before AWS can assign that ID:

1. Deploy with `owner_sub` empty to create the infrastructure. Every website
   model query is denied until an owner is configured.
2. Create your Cognito website login and retrieve its `sub` using the commands below.
3. Supply that ID, review/apply a second plan, and regenerate/upload the frontend
   config. Only that authenticated Cognito user can query the model through the website.

Initial owner configuration is empty and denies
all queries. Create the owner administratively after the pool exists, deliver
the invitation through Cognito, and complete the initial password challenge in
hosted login. Never pass passwords through Terraform or commit them in examples.
Read the owner's immutable `sub`, configure it, review a second plan, and apply
before enabling queries. Public registration remains disabled.

After an authorized initial deployment, use the pool ID from Terraform:

```sh
aws cognito-idp admin-create-user --profile PROFILE --region us-east-1 \
  --user-pool-id POOL_ID --username OWNER_EMAIL \
  --user-attributes Name=email,Value=OWNER_EMAIL Name=email_verified,Value=true \
  --desired-delivery-mediums EMAIL --query 'User.Username' --output text
```

Use your own email in place of `OWNER_EMAIL`; Cognito sends the temporary
password instead of putting it in source or Terraform. Do not use CLI debug
logging. Open hosted login with the browser application's Login button and
finish the first-password challenge there. To retrieve only the subject:

```sh
aws cognito-idp admin-get-user --profile PROFILE --region us-east-1 \
  --user-pool-id POOL_ID --username OWNER_EMAIL \
  --query "UserAttributes[?Name=='sub'].Value | [0]" --output text
```

Supply that value through the terminal without creating a tfvars file:

```sh
printf 'Owner Cognito subject: '
read -r -s TF_VAR_owner_sub
printf '\n'
export TF_VAR_owner_sub
terraform -chdir=infra/bedrock plan -var='monthly_budget_usd=5' -out=owner.tfplan
terraform -chdir=infra/bedrock show owner.tfplan
```

Keep the ARN/email environment variables available. Do not pass `-var='owner_sub='`
on this second plan: it would override the subject you just entered. After review
and approval, run `terraform -chdir=infra/bedrock apply owner.tfplan`, then regenerate
and upload the frontend config as shown above. Never configure the mutable email as the allowlist
identifier. Use S256 PKCE/state in the browser; the secretless Cognito client
permits only code flow. Explicit logout removes local session/history and calls
Cognito hosted logout. Access tokens already issued can remain valid until
their five-minute expiry; logout is not immediate server-side revocation of all
bearer tokens. A browser refresh may redirect to Cognito to regain an in-memory
token. Saved conversation messages and authentication are separate.

Securely back up local Terraform state: it can contain account identifiers and
email. Keep it for future updates/imports and teardown. Destroy only on an
explicit request after reviewing the managed resource list, nonempty frontend
and artifact buckets, and user-pool deletion. Teardown does not erase prior
charges or unrelated roles/access. Never delete state as a teardown substitute.

## Direct CLI and Python SDK usage

After deployment, configure an AssumeRole profile in your local AWS Config,
using the `cli_role_arn` output and an existing SSO-backed source profile:

```ini
[profile bedrock-invoke]
role_arn = arn:aws:iam::123456789012:role/REPLACE_WITH_CLI_ROLE
source_profile = REPLACE_WITH_SSO_PROFILE
region = us-east-1
```

The base caller needs `sts:AssumeRole` permission and must match the configured
trust principal. The SDK/CLI credential chain obtains expiring credentials;
do not put credentials in the browser or commit AWS Config/credential files.

From `backend/`:

```sh
AWS_PROFILE=bedrock-invoke sh examples/query.sh
PYTHONPATH=src pyenv exec pipenv run python -m bedrock_chat.cli --profile bedrock-invoke 'Why is the sky blue?'
```

Both use Nova Micro in us-east-1 and a 512-token output maximum, returning
answer text and token usage. The shell example asks a fixed sample question;
the Python example accepts a prompt. These calls are billable and bypass the
browser's Cognito layer through the separate IAM role. SDK tests and shell
stubs are offline; no successful live model invocation is claimed. Reuse the
cost guide formula for the reported input/output counts; these examples have
no conversation history. No silent model or regional fallback is implemented.

## Frontend controls, persistence, and verification

Run `npm --prefix frontend run dev` for local UI development. Tests supply fake
public config and authentication; real Cognito uses the deployed HTTPS root
callback. Never disable API/owner checks to make local login work.

Use Submit or Enter to ask a question; Shift+Enter inserts a newline and IME
composition does not submit. The composer prevents duplicate in-flight requests
and keeps a failed draft for deliberate retry. An arriving answer preserves any
new draft typed while waiting. Responses arrive complete after
loading. Copy answer copies only that answer, announces success after the
clipboard operation, and suggests manual selection if clipboard access fails.
The transcript follows new answers when near the bottom and preserves your
position while reading older messages.

Chrome stores the newest 100 completed exchanges, capped at 1 MiB serialized
UTF-8 JSON; oldest whole exchanges are removed with a retention notice. Model
context is separate: only the newest ten completed exchanges plus the prompt,
further bounded to 32,000 Unicode code points, are sent. Excluded history remains
saved, and the interface shows a distinct model-context notice. Refresh/reopen
retains messages, but tokens are in memory, and you may need to sign in again.
History is keyed by issuer and immutable owner subject and restored after owner
authentication; submission waits until restoration finishes. Invalid/unsupported/oversized records and unavailable/quota-bound
storage show a warning and allow memory-only operation.

Clear conversation keeps login and erases visible/saved messages, including after
session expiry or before sign-in. Failed erasure can be retried. Sign out also
clears the draft, in-memory tokens, transient PKCE state, and hosted login session.
A small owner-specific random generation marker contains no messages or tokens;
it invalidates in-flight responses across tabs even when no history existed.
Chrome Web Locks serialize history writes/erasure across tabs. Saves cannot
overwrite history changed by another tab; conflicting answers remain in
memory with a warning. After a cross-tab clear, submission waits for history to
reload, including any exchanges saved since that clear. A later clear or logout
invalidates the pending reload. Copy any unsaved answers before reloading to
restore the saved conversation. Late responses
cannot restore an erased conversation. If storage removal fails, the app explains
how to clear this site's data in Chrome; logout shows that warning before
redirecting. Owner-keying does not encrypt messages: same-origin JavaScript and
someone with the unlocked browser profile can read saved messages. Chrome site
data deletion removes local history; no server history database is created.

Canonical offline frontend checks:

```sh
npm --prefix frontend run test:coverage -- --runInBand
npm --prefix frontend run typecheck
npm --prefix frontend run build
node -e 'const r=require("./frontend/coverage/coverage-final.json"); for(const f of Object.values(r)) for(const k of ["s","f","b"]) for(const n of Object.values(f[k]).flat()) if(n===0) throw new Error("Uncovered application code")'
```

Jest instruments all executable application source, including entry/config,
storage/context, auth callbacks, and unimported files, with global/per-file 100%
statement/branch/function/line gates and JSON/LCOV reports. Application source
has no coverage exclusions. Tests cover HTML-like messages rendered as text,
in-memory tokens, URL replacement on callback success/failure, transient state
cleanup, and safe feedback. No live AWS account is used in unit tests.

The reviewable GitHub Actions workflow performs pinned clean installs, both
coverage gates and exact-counter checks, TypeScript/Vite builds, Linux adapter
packaging/smoke checks, and Terraform formatting/validation/mock tests. It has
no AWS credentials or deployment step. It has not been run by GitHub; local
checks are separate evidence. Current npm advisories concern Jest's development
dependency graph (glob/minimatch/deepmerge), which is not shipped in browser
assets. Treat source/test/config inputs as trusted; review upstream fixes before
running arbitrary third-party test configurations. Do not use `npm audit fix
--force` to downgrade/swap the test stack silently.

Before claiming deployment verification, test real Chrome login/follow-ups,
refresh/reopen, context/retention notices, clear/logout including another tab
and a late request, copy/keyboard/IME/scroll behavior, and rejection of missing,
expired, wrong-scope, and other-owner tokens without inference. Verify delivered
CSP/no-referrer/nosniff headers and actual enforced CSP, callback cleanup on
success/error and Back navigation, and no synthetic callback markers in enabled
logs. These checks remain separate from unit coverage and local adapter tests.

Teardown is only on request: review a destroy plan and project-managed buckets,
their contents, artifact object, and user pool first. Terraform deletes its
managed ZIP object; uploaded frontend objects must be removed deliberately
before the bucket can be destroyed. No `force_destroy` is enabled. Retain state
and backups until teardown is verified; earlier costs and unrelated account
permissions remain.

After all Terraform commands, including the owner-subject update, have finished,
clear the identifying inputs from that terminal:

```sh
unset TF_VAR_trusted_principal_arn TF_VAR_budget_email
```

## Troubleshooting

Expired credentials require refreshing the temporary profile, not static keys.
AccessDenied can mean missing caller AssumeRole permission, trust mismatch,
model access restrictions, or an organization policy. Quota errors require
waiting or reviewing the account quota; retries can incur cost. A missing owner
subject must fail closed. Budget emails can lag usage. Preserve diagnostics
without logging passwords, tokens, callback URLs, prompts, or responses.
