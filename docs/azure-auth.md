# Backend Entra token contract

Task 3.1, implemented November 16, 2026. This changes backend authorization only.
It does not create Entra registrations, deploy hosting or establish browser login.
Those remain later tasks. Tests use synthetic identities, locally generated RSA
keys, mocked Microsoft discovery/JWKS and a mocked model; no live inference occurs.

## Runtime inputs

| Environment variable | Required value |
| --- | --- |
| `AZURE_TENANT_ID` | Subscription directory's tenant UUID; shared with model configuration |
| `ENTRA_API_CLIENT_ID` | API registration's client UUID, the exact v2 access-token audience |
| `ENTRA_SPA_CLIENT_ID` | Distinct SPA registration's client UUID, the permitted `azp` |
| `ENTRA_OWNER_OBJECT_ID` | Owner's immutable object UUID inside that tenant |

Keep actual values in private runtime environment/input files. Documentation and
tests contain placeholders only. There are no passwords or client-secret inputs.
`AZURE_CLIENT_ID` remains the model's user-assigned managed identity client ID;
it is not interchangeable with either Entra application client ID above.
Missing/malformed auth settings, or identical SPA/API IDs, deny all model queries
without performing discovery. The legacy `ISSUER`, `CLIENT_ID` and `OWNER_SUB`
settings no longer configure backend authorization.

For v2 tokens the API audience is the plain API client UUID, not an `api://` URI
or the SPA client ID. The later browser configuration will request the full
`api://<api-client-id>/query` scope, while the access token must contain the
short `query` permission in its `scp` string. Email, display names and Cognito
subjects never determine access. Client/tenant IDs are identifiers rather than
credentials; some must be public in the browser sign-in configuration.

## Validation and cache behavior

The issuer is derived exclusively from the configured tenant:
`https://login.microsoftonline.com/<tenant-id>/v2.0`. The validator lazily fetches
that tenant's `.well-known/openid-configuration`, checks the exact issuer, and
uses its `jwks_uri`. Discovery redirects are rejected. Only HTTPS Microsoft
login-host JWKS URLs under the configured tenant or `common` are permitted;
token-supplied `jku`/`x5u` URLs never select the key endpoint.

Discovery and JWKS cache lifetimes are five minutes, with two-second network
operation timeouts. Discovery refresh is serialized within the app process.
PyJWT's non-expiring per-key cache is disabled. Its 30-second unknown-key refresh
cooldown bounds repeated refreshes; a newly rotated key can be rejected until
the cooldown expires. A successful refresh handles rotation. Discovery failure
at expiry or unavailable/invalid keys denies the request. Failed unknown-key
refresh does not authorize the unknown key or discard still-valid cached keys.
These are per-process caches and cooldowns, not a global ingress rate limit.

Accepted tokens must have a supported RS256 signature and signing-key issuer
bound to the configured tenant (exact issuer or Microsoft's tenant placeholder).
The pinned PyJWT preserves this Microsoft-specific key extension in its JWK data;
regression tests cover matching, templated, missing and foreign key issuers.
Unsupported critical signing-header extensions are rejected.

JWT verification requires exact issuer and a single exact API audience, integer
`exp`, `iat` and `nbf`, valid lifetime, `ver=2.0`, exact tenant `tid`, authorized SPA
`azp`, configured owner `oid`, and delegated `scp` containing `query`. ID tokens,
v1 tokens and app-only tokens are rejected. Optional `idtyp`, if provided,
must describe a user; roles cannot substitute for delegated scope. No email
claim is required. A changed display `sub` does not replace the immutable owner.

Every `/query` request is authorized before payload processing or inference.
Entra discovery/JWKS failures and invalid tokens return the existing fixed 401
message, without logging token contents, forged headers, prompts or raw provider
errors. Forwarded identity headers are ignored, including headers that carry an
otherwise valid token without a real Authorization bearer header.

## Verification and remaining work

The full backend suite passes 204 tests with exact 100% statement and branch
coverage and zero missing counters. Rejection tests go through Flask with a mock
model and assert no model calls. Tests cover default runtime wiring, absent/
malformed settings, signature/algorithm/lifetime/claims, realistic ID/app-only
tokens, attacker-controlled header URLs, discovery redirects/failures/cache
expiry/recovery, malformed JWKS, refresh cooldown, key rotation and refresh
failure. The production coverage configuration and dependency lock are unchanged.

Actual API/SPA registrations and delegated consent, browser OIDC and history
identity wiring, hosted configuration, and Chrome acceptance remain pending.
This offline result does not prove live owner sign-in. The existing Azure model
infrastructure remains unchanged by task 3.1.

Sources: [Microsoft claim validation](https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation),
[Microsoft issuer/signing-key validation](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens),
and the [pinned PyJWT API/cache behavior](https://pyjwt.readthedocs.io/en/latest/api.html).
