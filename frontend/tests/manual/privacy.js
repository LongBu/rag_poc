// Run on the deployed app in DevTools. No tokens or model requests are used.
(async () => {
  const violations = [];
  const listener = event => violations.push(event.effectiveDirective);
  document.addEventListener("securitypolicyviolation", listener);
  const probe = document.createElement("script");
  window.__azureCspProbeExecuted = false;
  probe.textContent = "window.__azureCspProbeExecuted = true;";
  try {
    document.head.append(probe);
    let connectionBlocked = false;
    try { await fetch("https://example.invalid/azure-csp-probe", {credentials: "omit"}); }
    catch { connectionBlocked = true; }
    await new Promise(resolve => setTimeout(resolve, 500));
    if (window.__azureCspProbeExecuted || !violations.some(v => v.startsWith("script-src"))) {
      throw new Error("Inline-script CSP enforcement was not confirmed");
    }
    if (!connectionBlocked || !violations.includes("connect-src")) {
      throw new Error("Connection CSP enforcement was not confirmed");
    }
    console.info("PASS: browser blocked inline script and disallowed connection through CSP.");
  } finally {
    probe.remove();
    document.removeEventListener("securitypolicyviolation", listener);
    delete window.__azureCspProbeExecuted;
  }
})();
