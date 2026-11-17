// Self-check fixture boundaries and refusal to overwrite existing browser data.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync(`${__dirname}/retention.js`, "utf8");
const config = {apiUrl: "https://chat.example", tenantId: "00000000-0000-0000-0000-000000000001", ownerObjectId: "00000000-0000-0000-0000-000000000002"};
(async () => {
  for (const mode of ["count", "bytes"]) {
    for (const occupied of [false, true]) {
      const storage = new Map(occupied ? [[`azure-chat:${config.tenantId}:${config.ownerObjectId}`, "keep me"]] : []);
      const context = {fetch: async () => ({ok: true, json: async () => config}), location: {origin: config.apiUrl}, TextEncoder,
        crypto: {randomUUID: () => "test-generation"}, console: {info() {}},
        navigator: {locks: {request: async (_, fn) => fn()}},
        localStorage: {getItem: k => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v)}};
      const run = vm.runInNewContext(source.replace('const mode = "count";', `const mode = "${mode}";`), context);
      if (occupied) {
        await assert.rejects(run, /Existing conversation state/);
        assert.equal([...storage.values()][0], "keep me");
        assert.equal(storage.size, 1);
      } else {
        await run;
        const raw = [...storage.values()].find(v => v.startsWith("{"));
        const data = JSON.parse(raw);
        assert.equal(data.exchanges.length, mode === "count" ? 100 : 12);
        assert.ok(Buffer.byteLength(raw) <= 1024 ** 2);
        if (mode === "bytes") assert.equal(Buffer.byteLength(raw), 1024 ** 2 - 1);
        assert.ok(JSON.stringify(data.exchanges.slice(-10)).length < 4000);
      }
    }
  }
  console.log("Retention fixtures pass count/byte boundaries, short model context and no-overwrite checks.");
})().catch(error => {console.error(error); process.exitCode = 1;});
