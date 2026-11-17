# Disposable live storage-retention checks

> Privacy: account names, application origins, image digests and request IDs in this document are synthetic placeholders; replace them before use.

Use a new, disposable **normal Chrome profile**, not your everyday profile.
Do not turn on Chrome sync for it. These fixtures contain only synthetic text.
They never read tokens, export data, clear existing data or overwrite existing
history. A preexisting history/generation key makes the snippet refuse to run.
Deleting the disposable profile afterward removes only its test-site data.

The local fixture self-check passes with:

```sh
node frontend/tests/manual/check-retention.cjs
```

It verifies both boundaries, short newest-ten model context, and refusal to
change preexisting conversation data. This is not proof of live UI behavior.

## Count limit

1. Create a new Chrome profile (without sync) and open the deployed site:
   https://chat.example.invalid
2. **Before signing in**, open DevTools → Sources → Snippets → New snippet.
3. Copy the contents of `frontend/tests/manual/retention.js` into the snippet.
   Leave `const mode = "count";`. Review it before running it.
4. Run the snippet. Console should report 100 synthetic exchanges seeded.
   If it refuses existing state, stop and use a fresh disposable profile.
5. Reload the app, sign in as the owner, and confirm the synthetic transcript
   appears. Do not Clear or Sign out between seeding and this test.
6. Send **Reply OK** once. This is one billable normal-cap request; no automatic
   retry is needed. Only the newest ten short pairs enter the model context.
7. Confirm the notice says **1 older exchanges removed by the storage retention
   limit.** The oldest `RETENTION count fixture 1` should disappear, fixture 2
   should remain, and the new answer should appear.
8. Reload/sign in and confirm the trimmed transcript stays trimmed.

## Size limit

Repeat in a **second fresh disposable Chrome profile**, changing the snippet's
mode to `"bytes"` before running it. This seeds 12 exchanges whose serialized
JSON occupies exactly **1,048,575 UTF-8 bytes** (1 MiB minus one). The large
oldest assistant answer contains synthetic `x` characters; it remains outside
the newest ten pairs sent to the model. User prompts remain short and valid.

After reload/sign-in, send **Reply OK** once. Saving the completed exchange must
cross 1 MiB and remove the large oldest exchange. Confirm the same retention
notice appears, `RETENTION bytes fixture 1` disappears, fixture 2 remains and
the new answer appears. Reload/sign in and confirm it remains trimmed.

Report both count and size notice results separately. The fixture self-check
already confirms initial sizes and safety, but these live UI/reopen results
remain pending until observed. Two successful manual runs require two deliberate
billable queries total; do not submit 101 requests to test retention.

## Live token rejection checks

From the repository root, `python3 backend/scripts/check-live-auth.py` uses the
existing selected Azure CLI identity and current private app outputs. It obtains
an existing developer Cognitive Services token through Azure CLI, holds it only
in process memory and never displays or persists it. It does not change app
registrations, users, permissions, browser settings or Azure resources.
Every POST has an **invalid empty prompt**: expected auth rejection is 401,
and validation still prevents inference if a credential were unexpectedly
accepted. A result other than 401 fails the check.

The script checks missing/malformed bearer, forged identity headers, alg=none,
HS256, missing signing-key ID, invalid RS256 signature with a real Microsoft key
ID, and a real Microsoft-issued token intended for Cognitive Services rather
than this API/SPA. That real token differs in multiple claims, so its rejection
is **not an isolated proof** of every audience/client/version check.

The full isolated live matrix still needs legitimately issued suitable tokens:
expired/not-yet-valid API token, ID token, API token missing query scope,
other tenant/client/owner and app-only API token. Tokens altered after issuance
only exercise invalid signatures. No alternate identities/registrations were
created, consent expanded or secrets added to manufacture these cases. Offline
adversarial auth tests cover these classes; live cases remain explicitly open.
Never paste token values into chat or save them in a fixture/document.
