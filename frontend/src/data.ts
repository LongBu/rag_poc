export type Config = {apiUrl: string; issuer: string; clientId: string; loginOrigin: string; ownerSub: string};
export type Exchange = {user: string; assistant: string; timestamp: number};
export type Usage = {input_tokens: number; output_tokens: number};
export type Answer = {text: string; usage: Usage};
export const record = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
export const count = (value: string) => Array.from(value).length;
export const validPrompt = (value: string) => value.trim().length > 0 && value.isWellFormed() && count(value) <= 4000;
export const bytes = (value: string) => new TextEncoder().encode(value).length;

export async function loadConfig(): Promise<Config> {
  const response = await fetch("/config.json", {cache: "no-store"});
  if (!response.ok) throw new Error("Configuration unavailable");
  const data: unknown = await response.json();
  if (!record(data)
      || typeof data.apiUrl !== "string" || !/^https:\/\/[a-z0-9]+\.execute-api\.us-east-1\.amazonaws\.com$/.test(data.apiUrl)
      || typeof data.issuer !== "string" || !/^https:\/\/cognito-idp\.us-east-1\.amazonaws\.com\/us-east-1_[a-zA-Z0-9]+$/.test(data.issuer)
      || typeof data.loginOrigin !== "string" || !/^https:\/\/[a-z0-9-]+\.auth\.us-east-1\.amazoncognito\.com$/.test(data.loginOrigin)
      || typeof data.clientId !== "string" || !/^[a-z0-9]+$/.test(data.clientId)
      || typeof data.ownerSub !== "string" || !(data.ownerSub === "" || /^[a-fA-F0-9-]{36}$/.test(data.ownerSub))) {
    throw new Error("Invalid configuration");
  }
  return {apiUrl: data.apiUrl, issuer: data.issuer, clientId: data.clientId, loginOrigin: data.loginOrigin, ownerSub: data.ownerSub};
}

export function context(exchanges: Exchange[], prompt: string) {
  const selected = exchanges.slice(-10);
  while (selected.length > 0 && count(prompt) + selected.reduce((n, pair) => n + count(pair.user) + count(pair.assistant), 0) > 32000) selected.shift();
  return {history: selected.map(({user, assistant}) => ({user, assistant})), omitted: exchanges.length - selected.length};
}

export async function query(config: Config, token: string, prompt: string, history: ReturnType<typeof context>["history"]): Promise<Answer> {
  const response = await fetch(`${config.apiUrl}/query`, {method: "POST", headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`}, body: JSON.stringify({prompt, history})});
  if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? "Sign in again to continue." : "The request failed. Check your connection, access, or quota and retry deliberately.");
  const data: unknown = await response.json();
  if (!record(data) || typeof data.text !== "string" || !data.text.trim() || !record(data.usage)
      || !Number.isSafeInteger(data.usage.input_tokens) || (data.usage.input_tokens as number) < 0
      || !Number.isSafeInteger(data.usage.output_tokens) || (data.usage.output_tokens as number) < 0) throw new Error("Invalid model response");
  return {text: data.text, usage: {input_tokens: data.usage.input_tokens as number, output_tokens: data.usage.output_tokens as number}};
}
