# Live privacy, callback and timing acceptance (task 6.3)

> Privacy: account names, application origins, image digests and request IDs in this document are synthetic placeholders; replace them before use.

Run after the agent's idle/scale-to-zero measurement is complete, so browser
activity does not invalidate that measurement. Use the deployed site in Chrome.
The files below are test-only; they are not included in the public image.
Self-check: `node frontend/tests/manual/check-browser-probes.cjs`.

## Enforced browser CSP

In DevTools → Sources → Snippets, review and run the contents of
`frontend/tests/manual/privacy.js`. It injects a harmless inline-script marker
and attempts a connection to `https://example.invalid/azure-csp-probe` without
credentials. Both must be blocked by the existing policy; the test requires
actual `securitypolicyviolation` events, not merely a network error. Expected:

`PASS: browser blocked inline script and disallowed connection through CSP.`

Chrome will also show expected CSP violations. The snippet removes its probe
and listener. No model calls or tokens are used; do not weaken CSP to pass it.
Normal owner sign-in and queries must continue working with CSP enforced.

## Callback URL cleanup

1. Sign out, sign in normally, and confirm the app's address is the clean HTTPS
   root, with no `code`, `state`, `session_state`, error values or token fragment.
2. Use Back navigation. If you return to the app, it must have the clean root URL
   without reprocessing/showing the callback. A Microsoft login page encountered
   during Back is not itself an app callback leak.
3. Test rejected callback cleanup by opening this synthetic URL in a separate
   tab (it contains no real code/token):
   https://chat.example.invalid/?code=azure63-invalid-code&state=azure63-invalid-state
4. The app should show safe sign-in failure feedback and replace the address
   with its clean root. Navigate away and Back; if the app reappears, synthetic
   callback parameters must not return. Sign in normally afterward if needed.

Report success/error cleanup and Back behavior separately. Never copy a real
callback URL or token into chat, screenshots, files or logs.

## Inference round-trip and overlap throttling

Use a signed-in tab. Review/run `frontend/tests/manual/inference-throttling.js`
in DevTools, then submit exactly **Reply OK** once through the normal app UI.
It temporarily intercepts only the next same-origin query request, restores
fetch immediately, and launches one additional synthetic overlap using the same
in-memory authorization headers. It does not display/persist those headers.
There are at most **two billable normal-cap (512 completion-token) requests**;
usually one succeeds and the other is rejected before inference. No retry is
performed. Do not repeat automatically if the outcome is inconclusive.

Expected console output: HTTP statuses containing **200 and 429**, plus batch
seconds. Either request may win admission; a first-request 429 can leave the UI
showing a safe retry error even if the second succeeds. The printed time is
end-to-end batch time (network/auth/inference), not pure model compute time.
Report only the status pair and seconds, never request headers or tokens.
Reload afterward to discard any console instrumentation. The helper self-check
verifies response preservation, at-most-two requests, cleanup, status handling
and absence of a synthetic secret from console output.

This observes overlapping-request throttling. The deterministic one-per-second/
burst-two token-bucket behavior remains verified by offline tests; process and
revision/restart limitations still apply. No scaling/rate setting is a monthly
spending cap.
