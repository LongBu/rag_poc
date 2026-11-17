import {User} from "oidc-client-ts";
import type {Config, Exchange} from "../src/data";
export const config: Config = {
  apiUrl: location.origin,
  issuer: "https://login.microsoftonline.com/00000000-0000-0000-0000-000000000001/v2.0",
  tenantId: "00000000-0000-0000-0000-000000000001",
  spaClientId: "00000000-0000-0000-0000-000000000003",
  apiAudience: "00000000-0000-0000-0000-000000000002",
  apiScope: "api://00000000-0000-0000-0000-000000000002/query",
  ownerObjectId: "00000000-0000-0000-0000-000000000004",
};
export const pair: Exchange = {user: "question", assistant: "answer", timestamp: 1};
export const user = () => new User({access_token: "synthetic", token_type: "Bearer", scope: `openid profile email ${config.apiScope}`, expires_at: Math.floor(Date.now()/1000)+300, profile: {tid: config.tenantId, oid: config.ownerObjectId, sub: "synthetic-pairwise-subject", iss: config.issuer, aud: config.spaClientId, exp: Math.floor(Date.now()/1000)+300, iat: Math.floor(Date.now()/1000)}});
export function locks() {
  Object.defineProperty(navigator, "locks", {configurable: true, value: {request: jest.fn((_name: string, callback: () => unknown) => Promise.resolve().then(callback))}});
}
