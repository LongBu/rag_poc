import {InMemoryWebStorage, UserManager, WebStorageStateStore, type User} from "oidc-client-ts";
import type {Config} from "./data";

const prefix = "bedrock.oidc.";
export function clearTransient() {
  for (const key of Object.keys(sessionStorage)) if (key.startsWith(prefix)) sessionStorage.removeItem(key);
}
export function manager(config: Config) {
  return new UserManager({
    authority: config.issuer, client_id: config.spaClientId, response_type: "code", response_mode: "query",
    scope: `openid profile email ${config.apiScope}`, redirect_uri: `${location.origin}/`, post_logout_redirect_uri: `${location.origin}/`,
    automaticSilentRenew: false, loadUserInfo: false,
    userStore: new WebStorageStateStore({store: new InMemoryWebStorage()}),
    stateStore: new WebStorageStateStore({store: sessionStorage, prefix}),
  });
}
export function validUser(user: User | null, config: Config): user is User {
  return user !== null && user.expired === false && user.access_token.length > 0 && config.ownerObjectId !== ""
    && user.profile.iss === config.issuer && user.profile.aud === config.spaClientId
    && user.profile.tid === config.tenantId && user.profile.oid === config.ownerObjectId && typeof user.scope === "string" && user.scope.split(" ").includes(config.apiScope);
}
export function captureCallback(): string | null {
  const url = new URL(location.href);
  const fragment = new URLSearchParams(url.hash.slice(1));
  if (!["code", "state", "error", "error_description", "session_state", "access_token", "id_token"].some(key => url.searchParams.has(key) || fragment.has(key))) return null;
  history.replaceState(null, "", "/");
  return url.href;
}
export async function finishCallback(auth: UserManager, url: string | null, config: Config): Promise<User | null> {
  if (url === null) return null;
  try {
    const user = await auth.signinRedirectCallback(url);
    if (!validUser(user, config)) throw new Error("Owner sign-in required");
    clearTransient();
    return user;
  } catch {
    await Promise.allSettled([auth.removeUser(), Promise.resolve().then(clearTransient)]);
    throw new Error("Sign-in failed. Please sign in again.");
  }
}

export async function signOut(auth: UserManager) {
  await auth.removeUser();
  clearTransient();
  await auth.signoutRedirect({post_logout_redirect_uri: `${location.origin}/`});
}
