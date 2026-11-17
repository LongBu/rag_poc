# Process-local inference admission

Task 4.2, November 16, 2026.

After bearer authentication and JSON/prompt/history validation, `/query` tries
to acquire one process-local inference slot without waiting. If another request
holds it, the new request receives fixed JSON and HTTP 429 before inference.
The admitted request also needs one token from a bucket with capacity two,
initially full, refilling at one token per second using a monotonic clock.
Fractional refill is retained and idle time cannot accumulate more than two.
A burst permits two sequential requests; it never permits concurrent inference.

Concurrency and rate denials share the sanitized response:
`Inference busy or rate limit reached; retry deliberately later`. They use the
normal privacy/security headers and no-store cache policy. There is no internal
queue or automatic retry. Busy rejections consume no rate token; authentication,
invalid input, readiness, preflight and static/config requests consume none.
An accepted request consumes a token even if the model or response serialization
fails. The slot is released in `finally` on success and all error paths, including
a rate rejection. The semaphore also serializes bucket updates, so a second
lock is unnecessary.

`backend/gunicorn.conf.py` selects one `gthread` worker and four request threads.
Run from `backend/` with `PYTHONPATH=src python -m gunicorn --config
gunicorn.conf.py 'bedrock_chat.app:create_app()'` in the locked environment.
The extra request threads let readiness and rejected overlaps finish while one
thread waits for inference. Tests validate these settings through the installed
Gunicorn configuration API; `--check-config` also passes. Task 4.3 now adds container binding, logging, control-socket settings and real
Linux HTTP smoke tests; see `azure-container.md`.

These are per-app-instance, per-process controls. The supported runtime creates
one app instance in one worker. Extra workers, replicas or overlapping revisions
have independent slots/buckets; restarting/recreating an app resets its bucket
to two. They do not constrain direct model API use or enforce a monthly spend
cap. Keep one worker and normal max-one replica; revision/restart overlap and
budget alert delay must still be considered when assessing cost.

Offline evidence: 261 backend tests pass with exact 100% statement/branch
coverage and zero missing counters. New deterministic tests use a fake clock
and thread events rather than sleeps to check burst/refill/capacity, overlapping
requests, readiness during blocked inference, non-consuming rejected input,
slot release after rate/provider/timeout/serialization errors, and reset on
app recreation. All provider-error cases also verify a subsequent request can
run. Existing dependency warnings remain unchanged. No model or Azure calls,
container deployment or live load check was performed for this task.

See the [Gunicorn thread settings](https://gunicorn.org/reference/settings/#threads).
