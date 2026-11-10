import {InMemoryWebStorage, UserManager, WebStorageStateStore, type User} from "oidc-client-ts";
import type {Config} from "./data";

const prefix = "bedrock.oidc.";
export function clearTransient() {
  for (const key of Object.keys(sessionStorage)) if (key.startsWith(prefix)) sessionStorage.removeItem(key);
}
export function manager(config: Config) {
  return new UserManager({
    authority: config.issuer, client_id: config.clientId, response_type: "code",
    scope: "openid email chat/query", redirect_uri: `${location.origin}/`, post_logout_redirect_uri: `${location.origin}/`,
    automaticSilentRenew: false, loadUserInfo: false,
    metadataSeed: {end_session_endpoint: `${config.loginOrigin}/logout`},
    userStore: new WebStorageStateStore({store: new InMemoryWebStorage()}),
    stateStore: new WebStorageStateStore({store: sessionStorage, prefix}),
  });
}
export function validUser(user: User | null, config: Config): user is User {
  return user !== null && user.expired === false && user.access_token.length > 0 && config.ownerSub !== ""
    && user.profile.sub === config.ownerSub && typeof user.scope === "string" && user.scope.split(" ").includes("chat/query");
}
export function captureCallback(): string | null {
  const url = new URL(location.href);
  if (!["code", "state", "error"].some(key => url.searchParams.has(key))) return null;
  history.replaceState(null, "", "/");
  return url.href;
}
export async function finishCallback(auth: UserManager, url: string | null, config: Config): Promise<User | null> {
  if (url === null) return null;
  try {
    const user = await auth.signinRedirectCallback(url);
    if (!validUser(user, config)) {
      await auth.removeUser();
      throw new Error("Owner sign-in required");
    }
    return user;
  } finally { clearTransient(); }
}
export async function signOut(auth: UserManager, config: Config) {
  await auth.removeUser();
  clearTransient();
  await auth.signoutRedirect({extraQueryParams: {client_id: config.clientId, logout_uri: `${location.origin}/`}});
}
