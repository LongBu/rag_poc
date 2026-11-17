// Arm once on the signed-in deployed app, then submit exactly: Reply OK
// At most two billable normal-cap queries. No token values are logged/persisted.
(() => {
  if (window.__azure63ProbeArmed) throw new Error("Probe already armed; reload to reset");
  const original = window.fetch;
  window.__azure63ProbeArmed = true;
  window.fetch = async function(input, options) {
    const url = new URL(typeof input === "string" ? input : input.url, location.href);
    if (url.origin !== location.origin || url.pathname !== "/query" || options?.method !== "POST") {
      return original.call(this, input, options);
    }
    window.fetch = original;
    delete window.__azure63ProbeArmed;
    const body = JSON.parse(options.body);
    if (body.prompt !== "Reply OK") throw new Error("Probe requires the synthetic prompt: Reply OK");
    const start = performance.now();
    const first = original.call(this, input, options);
    const overlap = original.call(this, `${location.origin}/query`, {
      ...options, body: JSON.stringify({prompt: "Reply OK", history: []}),
    });
    const checks = await Promise.allSettled([first, overlap]);
    const seconds = (performance.now() - start) / 1000;
    const statuses = checks.map(r => r.status === "fulfilled" ? r.value.status : "network error");
    console.info("Synthetic overlap HTTP statuses:", statuses, "batch seconds:", seconds.toFixed(3));
    if (!statuses.includes(200) || !statuses.includes(429)) {
      console.error("Live overlap check not confirmed; do not retry automatically.");
    } else console.info("PASS: one completed answer and one throttled overlap.");
    // Preserve the app's own original response. Never print its body/token headers.
    return first;
  };
  console.info("Armed. Submit Reply OK once. Reload afterward to discard the probe.");
})();
