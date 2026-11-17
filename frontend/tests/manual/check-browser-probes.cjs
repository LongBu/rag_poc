const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
(async () => {
  const read = name => fs.readFileSync(`${__dirname}/${name}`, "utf8");
  const events = new Map();
  let removed = false;
  const window = {};
  const context = {window, console: {info() {}}, setTimeout: fn => fn(),
    document: {addEventListener: (k, fn) => events.set(k, fn), removeEventListener: k => events.delete(k),
      createElement: () => ({remove() {removed = true;}}),
      head: {append() {events.get("securitypolicyviolation")({effectiveDirective: "script-src-elem"});}}},
    fetch: async () => {events.get("securitypolicyviolation")({effectiveDirective: "connect-src"}); throw new Error("CSP blocked");}};
  await vm.runInNewContext(read("privacy.js"), context);
  assert.ok(removed);
  assert.equal(events.size, 0);
  assert.equal(window.__azureCspProbeExecuted, undefined);
  for (const statuses of [[200, 429], [429, 200], [200, 200]]) {
    const calls = [], output = [], errors = [];
    const original = async (input, opts) => {calls.push([input, opts]); return {status: statuses[calls.length - 1]};};
    const window = {fetch: original};
    vm.runInNewContext(read("inference-throttling.js"), {window, URL, location: {origin: "https://chat.example"}, performance,
      console: {info: (...v) => output.push(v), error: (...v) => errors.push(v)}});
    const response = await window.fetch("https://chat.example/query", {method: "POST", body: '{"prompt":"Reply OK"}', headers: {Authorization: "Bearer synthetic-secret-marker"}});
    assert.equal(calls.length, 2);
    assert.equal(response.status, statuses[0]);
    assert.equal(window.fetch, original);
    assert.equal(window.__azure63ProbeArmed, undefined);
    assert.equal(errors.length, statuses.includes(429) ? 0 : 1);
    assert.ok(!JSON.stringify([...output, ...errors]).includes("synthetic-secret-marker"));
    assert.equal(JSON.parse(calls[1][1].body).prompt, "Reply OK");
  }
  console.log("Browser probes pass cleanup, two-request bound, response preservation and no-secret-output checks.");
})().catch(error => {console.error(error); process.exitCode = 1;});
