import {OidcClient} from "oidc-client-ts";
import {webcrypto} from "node:crypto";
import {captureCallback, clearTransient, finishCallback, manager, signOut, validUser} from "../src/auth";
import {config, user} from "./fixtures";
beforeEach(() => {localStorage.clear(); sessionStorage.clear(); history.replaceState(null, "", "/");});
afterEach(() => jest.restoreAllMocks());
test("PKCE, code flow, memory-only tokens and transient state", async () => {
  const auth = manager(config);
  expect(auth.settings.disablePKCE).toBe(false);
  expect(auth.settings.response_type).toBe("code");
  expect(auth.settings.scope).toBe(`openid profile email ${config.apiScope}`);
  expect(auth.settings.automaticSilentRenew).toBe(false);
  expect(auth.settings.loadUserInfo).toBe(false);
  expect(auth.settings.metadataUrl).toBe(`${config.issuer}/.well-known/openid-configuration`);
  await auth.storeUser(user());
  expect((await auth.getUser())!.access_token).toBe("synthetic");
  expect(localStorage.length).toBe(0); expect(sessionStorage.length).toBe(0);
  await auth.settings.stateStore.set("state", "transient verifier");
  sessionStorage.setItem("unrelated", "keep"); clearTransient();
  expect(sessionStorage.getItem("bedrock.oidc.state")).toBeNull();
  expect(sessionStorage.getItem("unrelated")).toBe("keep");
});
test("owner, expiry, token and scope checks", () => {
  expect(validUser(user(), config)).toBe(true);
  expect(validUser(null, config)).toBe(false);
  expect(validUser(user(), {...config, ownerObjectId: ""})).toBe(false);
  for (const changes of [{expires_at: 1}, {expires_at: undefined}, {access_token: ""}, {profile: {...user().profile, oid: "other"}}, {scope: undefined}, {scope: "openid"}]) expect(validUser(Object.assign(user(), changes), config)).toBe(false);
});
test.each(["code=private&state=private", "state=private", "error=private&error_description=private"])("callback URL is removed: %s", query => {
  history.replaceState(null, "", `/?${query}`);
  expect(captureCallback()).toContain(query);
  expect(location.href).toBe("https://localhost/");
  expect(captureCallback()).toBeNull();
});
test("callback success and no callback", async () => {
  const auth = manager(config), owner = user();
  jest.spyOn(auth, "signinRedirectCallback").mockResolvedValue(owner);
  sessionStorage.setItem("bedrock.oidc.pending", "verifier");
  expect(await finishCallback(auth, "https://localhost/?code=code&state=state", config)).toBe(owner);
  expect(sessionStorage.length).toBe(0);
  expect(await finishCallback(auth, null, config)).toBeNull();
});
test.each(["wrong-owner", "failed-exchange"])("failed callback cleans state: %s", async kind => {
  const auth = manager(config);
  const callback = jest.spyOn(auth, "signinRedirectCallback");
  if (kind==="wrong-owner") callback.mockResolvedValue(Object.assign(user(), {profile: {...user().profile, oid: "other"}}));
  else callback.mockRejectedValue(new Error("private callback values"));
  sessionStorage.setItem("bedrock.oidc.pending", "verifier");
  await expect(finishCallback(auth, "https://localhost/?error=private", config)).rejects.toThrow();
  expect(sessionStorage.length).toBe(0);
});
test("logout removes tokens, transient state and calls the OIDC logout manager", async () => {
  const auth = manager(config); await auth.storeUser(user());
  sessionStorage.setItem("bedrock.oidc.pending", "verifier");
  const redirect = jest.spyOn(auth, "signoutRedirect").mockResolvedValue();
  await signOut(auth);
  expect(await auth.getUser()).toBeNull(); expect(sessionStorage.length).toBe(0);
  expect(redirect).toHaveBeenCalledWith({post_logout_redirect_uri: "https://localhost/"});
});
test.each(["iss", "aud", "tid", "oid"])("rejects mismatched or missing %s", claim => {
  for (const value of ["other", undefined]) {
    const owner = user(); owner.profile[claim] = value;
    expect(validUser(owner, config)).toBe(false);
  }
});
test("authorization uses tenant and object ID without email or matching subject", () => {
  const owner = user(); owner.profile.sub = "pairwise-subject";
  expect(owner.profile.email).toBeUndefined();
  expect(validUser(owner, config)).toBe(true);
});
test.each(["#code=private&state=private", "#access_token=private", "#id_token=private", "?error_description=private", "?session_state=private"])("scrubs unexpected callback material %s", suffix => {
  history.replaceState(null, "", `/${suffix}`);
  expect(captureCallback()).toContain("private");
  expect(location.href).toBe("https://localhost/");
});
test("ordinary URL is left alone", () => {
  history.replaceState(null, "", "/?view=chat#messages");
  expect(captureCallback()).toBeNull();
  expect(location.search).toBe("?view=chat");
});
test("callback exchange failure removes existing memory tokens and hides provider error", async () => {
  const auth = manager(config); await auth.storeUser(user());
  jest.spyOn(auth, "signinRedirectCallback").mockRejectedValue(new Error("private-code-token"));
  sessionStorage.setItem("bedrock.oidc.pending", "private-verifier");
  await expect(finishCallback(auth, "https://localhost/?error=private", config)).rejects.toThrow("Sign-in failed. Please sign in again.");
  expect(await auth.getUser()).toBeNull();
  expect(sessionStorage.length).toBe(0); expect(localStorage.length).toBe(0);
});
test("cleanup failure rejects login and removes memory tokens", async () => {
  const auth = manager(config); await auth.storeUser(user());
  jest.spyOn(auth, "signinRedirectCallback").mockResolvedValue(user());
  sessionStorage.setItem("bedrock.oidc.pending", "verifier");
  jest.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {throw new Error("private");});
  await expect(finishCallback(auth, "https://localhost/?code=private", config)).rejects.toThrow("Sign-in failed. Please sign in again.");
  expect(await auth.getUser()).toBeNull();
});
test("real callback rejects unknown state without retaining tokens", async () => {
  const auth = manager(config); await auth.storeUser(user());
  await expect(finishCallback(auth, "https://localhost/?code=private&state=unknown", config)).rejects.toThrow("Sign-in failed. Please sign in again.");
  expect(await auth.getUser()).toBeNull(); expect(sessionStorage.length).toBe(0);
});

test("SDK creates S256 PKCE, nonce/state and Entra logout with no token hint", async () => {
  Object.defineProperty(crypto, "subtle", {configurable: true, value: webcrypto.subtle});
  const auth = manager(config);
  const client = new OidcClient({...auth.settings, metadata: {
    issuer: config.issuer,
    authorization_endpoint: `${config.issuer}/authorize`,
    end_session_endpoint: `${config.issuer}/logout`,
  }});
  const request = await client.createSigninRequest({nonce: "synthetic-nonce"});
  const params = new URL(request.url).searchParams;
  expect(params.get("client_id")).toBe(config.spaClientId);
  expect(params.get("scope")).toBe(`openid profile email ${config.apiScope}`);
  expect(params.get("response_mode")).toBe("query");
  expect(params.get("code_challenge_method")).toBe("S256");
  expect(params.get("code_challenge")).toMatch(/^[A-Za-z0-9_-]{43}$/);
  expect(params.get("nonce")).toBe("synthetic-nonce");
  expect(params.get("state")).toBe(request.state.id);
  expect(params.has("code_verifier")).toBe(false);
  expect(await auth.settings.stateStore.get(request.state.id)).toContain("code_verifier");
  expect(localStorage.length).toBe(0);
  clearTransient(); expect(sessionStorage.length).toBe(0);
  const logout = new URL((await client.createSignoutRequest({})).url);
  expect(logout.pathname).toBe(new URL(`${config.issuer}/logout`).pathname);
  expect(logout.searchParams.getAll("client_id")).toEqual([config.spaClientId]);
  expect(logout.searchParams.get("post_logout_redirect_uri")).toBe("https://localhost/");
  expect(logout.searchParams.has("logout_uri")).toBe(false);
  expect(logout.searchParams.has("id_token_hint")).toBe(false);
});
