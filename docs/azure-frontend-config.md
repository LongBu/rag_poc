# Public Azure frontend configuration

Task 3.2, November 16, 2026. The frontend now accepts a public Azure configuration
contract, replacing the AWS URL/identity shape. Its values are identifiers and a
same-origin URL, not passwords, private tokens or model credentials.

## JSON fields and backend alignment

| Field | Validation / corresponding backend setting |
| --- | --- |
| `tenantId` | Tenant UUID; `AZURE_TENANT_ID` |
| `spaClientId` | SPA client UUID; `ENTRA_SPA_CLIENT_ID` |
| `apiAudience` | Distinct API client UUID, without `api://`; `ENTRA_API_CLIENT_ID` |
| `apiScope` | Exactly `api://<apiAudience>/query`, with the canonical lowercase API UUID |
| `ownerObjectId` | Owner UUID in that tenant; `ENTRA_OWNER_OBJECT_ID` |
| `issuer` | Exactly `https://login.microsoftonline.com/<tenantId>/v2.0`, with canonical lowercase tenant UUID |
| `apiUrl` | Exactly the current browser origin, with HTTPS required |

UUID values are validated in full and returned in canonical lowercase. Empty,
missing, wrong-type and malformed values are rejected. API and SPA IDs must be
different, including case-only variants. Common/organizations/foreign-tenant
issuers, spoofed authority hosts, mismatched or extra scopes, cross-origin API
URLs, embedded URL credentials and path/query variants are rejected. Old AWS
configuration does not provide a fallback.

`/config.json` is fetched with `cache: no-store`. The loader returns only the
seven allowlisted public fields; unknown fields are not propagated into the
application config object. This does not make a server response containing a
secret safe. Task 4.1's Flask runtime-config route itself constructs only these
seven fields before sending JSON to the browser; see `azure-web.md`. Never put client secrets, API keys or private
runtime inputs in that public response. Actual deployment identities remain
parameterized; tests use synthetic UUIDs only.

The browser origin must use HTTPS, including local testing of this contract.
The API URL contains no path or trailing slash; requests append `/query` at that
same origin. This contract is independent of a particular Azure hosting FQDN.

## Scope and verification

Shared callers and fixtures use `spaClientId` and `ownerObjectId`. The AWS-only
logout endpoint seed is removed so the OIDC library uses discovery metadata.
Task 3.3 now requests the delegated scope, checks ID-token tenant/object identity,
and adapts callback/logout handling; see `azure-browser-auth.md`. Task 3.4 now keys history by the Azure tenant and owner object ID; see
`azure-history.md`. Test subjects differ from object IDs to verify that the
application does not rely on pairwise subjects for saved-history identity.

Frontend verification after task 4.1: 169 tests across six suites; exact 100%
statements, branches, functions and lines, with every raw counter nonzero.
Strict TypeScript and the Vite production build pass. Live Azure sign-in remains
unverified until app registrations and hosting are provisioned.

Coverage collection/gates and dependency locks are unchanged. No cloud resources
or billable model calls are involved.
