# Azure browser authentication

Task 3.3, November 16, 2026.

The existing oidc-client-ts integration uses tenant-specific Entra discovery,
authorization-code flow with S256 PKCE, a fresh nonce per sign-in, query-mode
callbacks and `openid profile email` plus the configured full delegated API
scope. Email is optional and is never used for authorization.

Browser acceptance requires an unexpired access token, the delegated scope,
and ID-token issuer, SPA audience, tenant (`tid`) and owner object ID (`oid`)
matching public configuration. The pairwise subject is not the owner check.
The API remains responsible for cryptographic access-token signature/lifetime
validation and its full authorization contract; browser checks do not replace it.

Tokens live only in the SDK's in-memory user store. Redirect state and PKCE
verifiers temporarily occupy namespaced sessionStorage. Callback URLs, including
unexpected token/error fragments, are replaced with `/` before configuration
loading. Successful or failed callbacks remove transient state. Failed exchange,
identity validation or cleanup removes any in-memory user and returns fixed
error text, excluding raw provider details.

Logout first removes local tokens/transient state, then uses Entra's discovered
end-session endpoint with the registered post_logout_redirect_uri. The SDK adds
the SPA client_id. No Cognito logout_uri or ID-token hint is sent; Entra may ask
which session to sign out. Registration of exact redirect/logout URLs remains
an infrastructure task.

Offline evidence: 168 frontend tests in six suites, exact 100% statement/branch/
function/line coverage, TypeScript and production build. Tests exercise SDK PKCE
request generation, state rejection, nonce, claims, callback cleanup, token
storage and logout request parameters. Existing chat controls remain passing.
No live Entra browser sign-in, deployment or model request was performed.
Task 3.4 completes tenant/object-ID history wiring; see `azure-history.md`.
Live browser acceptance remains 6.2/6.3.
