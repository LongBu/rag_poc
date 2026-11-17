# Same-origin Flask shell and privacy headers

Task 4.1, November 16, 2026.

`create_app(..., frontend_dir=...)` serves a trusted Vite production build.
The default directory is `backend/src/bedrock_chat/static/`, beside the Python
modules. Source checkouts can pass `frontend/dist` explicitly after a Vite build.
The container task will copy the built files into that default directory;
task 4.3 now copies the production build into that directory (`azure-container.md`).
Hosting is still undeployed.
Missing builds return a sanitized JSON 404.

Only `/` and `/assets/<hashed-filename>` serve files. Asset names must match
Vite's name/hash/extension pattern; source maps, nested paths, dotfiles and
unhashed filenames are excluded. Resolved paths must stay inside the build
root, including symlink targets. No SPA catch-all or Flask default static route
can turn an unknown API route into HTML or expose arbitrary project files.
HTML uses `no-cache` with ETag revalidation. Successful hashed assets use
`public, max-age=31536000, immutable`, including conditional 304 responses.
Config, API responses and errors use `no-store`.

`/config.json` constructs exactly the seven public fields documented in
`azure-frontend-config.md`. It uses the validated Entra UUIDs and configured
HTTPS `FRONTEND_ORIGIN` (no trailing slash/path/query/credentials), never Host
or forwarded headers. Missing/invalid identity or origin returns fixed JSON
and 503. Model endpoints, managed-identity configuration, secrets, email and
other environment values are not serialized or injected into HTML or assets.
A fresh runtime config response changes no build files. `/ready` remains public
and checks model configuration without calling inference or acquiring a token.
`/query` retains bearer-token authorization; the old cross-origin CORS allowance
is removed. Direct authorized CLI clients do not depend on CORS.

Every response, including errors, carries enforced CSP, `Referrer-Policy:
no-referrer`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and HSTS
with a one-year max-age. CSP denies resources by default, allows bundled scripts,
styles/images/fonts from the same origin, and permits script connections only
to that origin and the configured tenant's exact discovery and token URLs.
It denies framing, plugins, base URLs and form navigation; inline scripts/eval
are not enabled. Browser redirect navigation to Entra is separate from script
connections. HTTPS ingress and disabled callback-bearing access logs remain
container/hosting tasks. Header delivery tests do not prove live Chrome CSP
or TLS enforcement; those checks remain tasks 6.2/6.3.

Verification: 253 backend tests and 169 frontend tests pass with exact 100%
coverage. Tests cover routes, cache revalidation, traversal and escaping symlinks,
malformed public config, forged Host/forwarded headers, no-secret public output,
public readiness, denied anonymous inference, security headers, and inert
HTML-like model and saved-history messages. TypeScript/Vite production build and
Flask test-client smoke delivery of that actual build pass. Tests and fixtures
use synthetic identifiers/secrets and mocked inference; no Azure calls occur.
Task 4.3 now builds and smoke-tests the image; no image has been published.
Full image-layer secret checks remain task 4.6.

Header choices follow [Flask security guidance](https://flask.palletsprojects.com/en/stable/web-security/)
and [CSP connect-src semantics](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/connect-src).
