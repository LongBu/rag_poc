import {captureCallback, clearTransient, finishCallback, manager, signOut, validUser} from "../src/auth";
import {config, user} from "./fixtures";
beforeEach(() => {localStorage.clear(); sessionStorage.clear(); history.replaceState(null, "", "/");});
afterEach(() => jest.restoreAllMocks());
test("PKCE, code flow, memory-only tokens and transient state", async () => {
  const auth = manager(config);
  expect(auth.settings.disablePKCE).toBe(false);
  expect(auth.settings.response_type).toBe("code");
  expect(auth.settings.scope).toBe("openid email chat/query");
  expect(auth.settings.automaticSilentRenew).toBe(false);
  expect(auth.settings.loadUserInfo).toBe(false);
  expect(auth.settings.metadataUrl).toBe(`${config.issuer}/.well-known/openid-configuration`);
  expect(auth.settings.metadataSeed).toEqual({end_session_endpoint: `${config.loginOrigin}/logout`});
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
  expect(validUser(user(), {...config, ownerSub: ""})).toBe(false);
  for (const changes of [{expires_at: 1}, {expires_at: undefined}, {access_token: ""}, {profile: {...user().profile, sub: "other"}}, {scope: undefined}, {scope: "openid"}]) expect(validUser(Object.assign(user(), changes), config)).toBe(false);
});
test.each(["code=private&state=private", "state=private", "error=private&error_description=private"])("callback URL is removed: %s", query => {
  history.replaceState(null, "", `/?${query}`);
  expect(captureCallback()).toContain(query);
  expect(location.href).toBe("http://localhost/");
  expect(captureCallback()).toBeNull();
});
test("callback success and no callback", async () => {
  const auth = manager(config), owner = user();
  jest.spyOn(auth, "signinRedirectCallback").mockResolvedValue(owner);
  sessionStorage.setItem("bedrock.oidc.pending", "verifier");
  expect(await finishCallback(auth, "http://localhost/?code=code&state=state", config)).toBe(owner);
  expect(sessionStorage.length).toBe(0);
  expect(await finishCallback(auth, null, config)).toBeNull();
});
test.each(["wrong-owner", "failed-exchange"])("failed callback cleans state: %s", async kind => {
  const auth = manager(config);
  const callback = jest.spyOn(auth, "signinRedirectCallback");
  if (kind==="wrong-owner") callback.mockResolvedValue(Object.assign(user(), {profile: {...user().profile, sub: "other"}}));
  else callback.mockRejectedValue(new Error("private callback values"));
  sessionStorage.setItem("bedrock.oidc.pending", "verifier");
  await expect(finishCallback(auth, "http://localhost/?error=private", config)).rejects.toThrow();
  expect(sessionStorage.length).toBe(0);
});
test("logout removes tokens, transient state and uses Cognito logout", async () => {
  const auth = manager(config); await auth.storeUser(user());
  sessionStorage.setItem("bedrock.oidc.pending", "verifier");
  const redirect = jest.spyOn(auth, "signoutRedirect").mockResolvedValue();
  await signOut(auth, config);
  expect(await auth.getUser()).toBeNull(); expect(sessionStorage.length).toBe(0);
  expect(redirect).toHaveBeenCalledWith({extraQueryParams: {client_id: config.clientId, logout_uri: "http://localhost/"}});
});
