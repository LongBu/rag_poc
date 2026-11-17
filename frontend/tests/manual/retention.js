// Run only in a disposable Chrome profile on the deployed app, before sign-in.
// Set mode to "count" or "bytes"; each run requires empty conversation storage.
(async () => {
  const mode = "count";
  if (!["count", "bytes"].includes(mode)) throw new Error("Unknown retention fixture");
  const response = await fetch("/config.json", {cache: "no-store"});
  if (!response.ok) throw new Error("Public configuration unavailable");
  const config = await response.json();
  const uuid = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
  if (config.apiUrl !== location.origin || !uuid.test(config.tenantId) || !uuid.test(config.ownerObjectId)) {
    throw new Error("Unexpected app identity/origin");
  }
  const key = `azure-chat:${config.tenantId}:${config.ownerObjectId}`;
  const exchanges = Array.from({length: mode === "count" ? 100 : 12}, (_, i) => ({
    user: `RETENTION ${mode} fixture ${i + 1}`,
    assistant: "Synthetic test answer.", timestamp: i,
  }));
  const data = {version: 1, exchanges};
  if (mode === "bytes") {
    // The large oldest answer stays outside the newest ten pairs sent to the model.
    const available = 1024 ** 2 - 1 - new TextEncoder().encode(JSON.stringify(data)).length;
    exchanges[0].assistant += "x".repeat(available);
  }
  const raw = JSON.stringify(data);
  await navigator.locks.request(key, () => {
    if (localStorage.getItem(key) !== null || localStorage.getItem(`${key}:generation`) !== null) {
      throw new Error("Existing conversation state found. Use a fresh disposable Chrome profile.");
    }
    localStorage.setItem(`${key}:generation`, crypto.randomUUID());
    localStorage.setItem(key, raw);
  });
  console.info(`Seeded ${exchanges.length} synthetic exchanges (${new TextEncoder().encode(raw).length} bytes). Reload, sign in, then send: Reply OK`);
})();
