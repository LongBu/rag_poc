# Linux container build and HTTP verification

Task 4.3, November 16, 2026.

From the repository root:

```sh
sh backend/scripts/build-container.sh
python3 backend/scripts/smoke-container.py
```

The canonical application build is now the root `Dockerfile`, producing local
`private-azure-chat:local` for Linux/amd64. It builds TypeScript/Vite in a Node
stage and installs hash-checked production dependencies from Pipfile.lock in a
separate Python stage, after Pipenv lock verification. Neither Node, npm build
dependencies, Pipenv, pytest, test services nor Lambda adapters enter the final
application image. The root `.dockerignore` allowlists only required source,
build configuration and dependency manifests. It excludes state/plans, private
inputs, cloud credentials, .git, environment files, chat data and generated output.
No runtime tenant/owner/model/email settings are passed at build time.

Bases are pinned by platform-specific Linux/amd64 manifests, verified against
the public registry on this date:

- `node:24.22.3-bookworm-slim@sha256:0e2646ab57e77b7a384a0cb59b6815b182c77e1f9c3ba36bd8435bd9c4e6680e`
- `python:3.14.8-slim-trixie@sha256:9b629e83e1a517e01eaf7a36362563c0c7f620d3e4747f7dcf79564e290b7b48`

The Python patch matches `.python-version`. Production dependencies retain exact
locks, binary-wheel installation and `pip check`; base updates require a fresh
build and verification rather than following mutable tags.

Gunicorn loads `backend/gunicorn.conf.py`: one gthread worker, four threads,
`0.0.0.0:8000`, 30-second worker timeout, no control socket, no access log,
warning/error diagnostics to stderr and worker temporary files in `/tmp`.
The final image runs as UID/GID 10001, with bytecode writes disabled and tracing
disabled. It contains only the Python package, built frontend and Gunicorn config
under `/app`. Flask serves the assets from its default package/static directory.
Public identity config is generated at runtime, never baked into static files.
Readiness validates model settings without inference; missing settings remain
unready and queries remain denied. Provide the non-secret runtime settings from
`azure-auth.md`, `azure-frontend-config.md` and the model configuration contract.

The smoke script runs real Gunicorn HTTP twice: once using the unmodified
production entry point with synthetic configuration and denied queries, then
with an explicit test WSGI target mounted read-only at `/smoke`. Only this test
target injects synthetic authentication/model services; it is not in the image.
Each container has a read-only root, a 64 MiB writable noexec/nosuid `/tmp`, no
capabilities, no-new-privileges and `--network none`. HTTP clients execute inside
the same network namespace against loopback; no host port or cloud connection
is needed. No credentials or host cloud directories are mounted. Containers are
stopped and removed on success or failure.

Verified locally on Docker Desktop with Linux/amd64 emulation: pinned image
build, strict frontend types/build, installed dependency consistency, non-root
and filesystem constraints, production startup/readiness, actual built assets,
allowlisted config, auth/validation/404/preflight, mocked success/usage and
503/504/502 errors. A blocked synthetic model verifies 429 without a second
invocation, readiness during inference and slot release afterward. Docker log
checks verify safe categories on stderr, no stdout, and absence of synthetic
callback/prompt/token/raw-exception markers. Image/runtime assertions verify
architecture, production-only packages, no embedded runtime config and no
Lambda adapter. Backend regression tests remain 261 with exact 100% coverage.

The owner has published the reviewed image, and independent anonymous digest pulls
plus full layer/history review pass; see `azure-release.md`. Identity-only
bootstrap is applied, while hosting/managed-identity inference/browser acceptance
remain pending. CI now runs these container checks and both Azure Terraform
roots, without credentials, publication or deployment. Obsolete Lambda packaging,
emulator fixtures, AWS Terraform and IAM/cost setup documents have been removed
after their Azure equivalents passed. Historical AWS OpenSpec artifacts and all
private state/backups are preserved. No cloud resources were changed by cleanup.
