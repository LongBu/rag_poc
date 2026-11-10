import {User} from "oidc-client-ts";
import type {Config, Exchange} from "../src/data";
export const config: Config = {apiUrl: "https://abc.execute-api.us-east-1.amazonaws.com", issuer: "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test", clientId: "client", loginOrigin: "https://chat.auth.us-east-1.amazoncognito.com", ownerSub: "12345678-1234-1234-1234-123456789012"};
export const pair: Exchange = {user: "question", assistant: "answer", timestamp: 1};
export const user = () => new User({access_token: "synthetic", token_type: "Bearer", scope: "openid chat/query", expires_at: Math.floor(Date.now()/1000)+300, profile: {sub: config.ownerSub, iss: config.issuer, aud: config.clientId, exp: Math.floor(Date.now()/1000)+300, iat: Math.floor(Date.now()/1000)}});
export function locks() {
  Object.defineProperty(navigator, "locks", {configurable: true, value: {request: jest.fn((_name: string, callback: () => unknown) => Promise.resolve().then(callback))}});
}
