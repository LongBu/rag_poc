# Azure saved-history identity

Task 3.4, November 16, 2026.

Saved history uses `azure-chat:<tenantId>:<ownerObjectId>` and its matching
`:generation` key. Configuration validates these UUIDs and the browser accepts
only an authenticated user whose tenant/object claims match it. Initial invalid
users cannot restore history. The Entra pairwise `sub` and optional email do
not determine history identity. Restore, cross-tab refresh, clear and logout
use the same tenant/owner key, including clear before sign-in or after expiry.

The existing version-1 payload, newest-100-exchange and 1 MiB UTF-8 retention
limits are unchanged. Navigator locks serialize the same owner key, generation
guards reject late responses after clear/logout, and epoch/snapshot checks
prevent stale tabs from resurrecting or overwriting history. Storage failures
remain visible and allow in-memory conversation. Model context remains bounded
to ten pairs independently of retained messages.

AWS-origin history is not automatically migrated. Browser storage is isolated
by origin, and the Azure namespace also ignores old provider/subject keys on
the same origin. Existing AWS or legacy records are neither imported nor deleted
by Azure clear/logout. To erase those records, clear site data for the old AWS
origin (and any old same-origin deployment) in Chrome settings. No server-side
history transfer is implemented. Saved messages remain readable to same-origin
scripts and anyone with access to the unlocked browser profile.

Offline verification: 168 tests across six frontend suites pass with exact
100% statements/branches/functions/lines and positive raw coverage counters;
TypeScript and production build pass. Coverage includes tenant/owner/provider
isolation, subject changes, restore after authentication, scoped erasure,
retention, locks, cross-tab clear, late logout response, context notices, copy,
keyboard/IME, scroll behavior and existing chat controls. No live browser or
Azure deployment check was performed; those remain tasks 6.2/6.3.
