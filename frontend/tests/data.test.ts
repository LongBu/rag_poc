import {bytes, context, count, loadConfig, query, record, validPrompt} from "../src/data";
import {config, pair} from "./fixtures";

beforeEach(() => {global.fetch = jest.fn();});
const fetchMock = () => jest.mocked(fetch);
function reply(data: unknown, status=200) {fetchMock().mockResolvedValue({ok: status<400, status, json: async () => data} as Response);}
test("Unicode counts and prompt validation", () => {
  expect(record({})).toBe(true);
  for (const value of [null, [], 1, ""]) expect(record(value)).toBe(false);
  expect(count("😀é")).toBe(2);
  expect(bytes("😀")).toBe(4);
  for (const value of ["", " ", "\ud800", "a".repeat(4001)]) expect(validPrompt(value)).toBe(false);
  expect(validPrompt("😀".repeat(4000))).toBe(true);
});
test("config loading", async () => {
  reply(config); expect(await loadConfig()).toEqual(config);
  reply({...config, ownerSub: ""}); expect((await loadConfig()).ownerSub).toBe("");
  expect(fetch).toHaveBeenCalledWith("/config.json", {cache: "no-store"});
  reply({}, 500); await expect(loadConfig()).rejects.toThrow("Configuration unavailable");
});
test.each([null, [], ...Object.keys(config).flatMap(key => [{...config, [key]: null}, {...config, [key]: "invalid!"}])])("invalid config %#", async value => {
  reply(value); await expect(loadConfig()).rejects.toThrow("Invalid configuration");
});
test("context preserves order, whole pairs, and saved history", () => {
  const pairs = Array.from({length: 12}, (_, i) => ({...pair, user: String(i)}));
  expect(context(pairs, "hi")).toEqual({history: pairs.slice(-10).map(({user, assistant}) => ({user, assistant})), omitted: 2});
  expect(context([], "hi")).toEqual({history: [], omitted: 0});
  expect(context([{...pair, assistant: "a".repeat(32000)}], "hi").history).toEqual([]);
  const exact = {...pair, user: "a", assistant: "😀".repeat(31998)};
  expect(context([exact], "a").history).toHaveLength(1);
  expect(context([exact], "ab").history).toHaveLength(0);
  expect(pairs).toHaveLength(12);
});
test("query payload and token usage", async () => {
  const answer = {text: "answer", usage: {input_tokens: 10, output_tokens: 2}};
  reply(answer); expect(await query(config, "token", "hi", [])).toEqual(answer);
  expect(fetch).toHaveBeenCalledWith(`${config.apiUrl}/query`, {method: "POST", headers: {"Content-Type": "application/json", Authorization: "Bearer token"}, body: JSON.stringify({prompt: "hi", history: []})});
});
test.each([400, 401, 403, 429, 500])("safe query status %i", async status => {
  reply({error: "private"}, status);
  await expect(query(config, "token", "hi", [])).rejects.toThrow(status===401 || status===403 ? "Sign in again" : "request failed");
});
test.each([null, {text: 1}, {text: " "}, {text: "ok", usage: null},
  ...["input_tokens", "output_tokens"].flatMap(key => [null, -1, 1.5].map(value => ({text: "ok", usage: {input_tokens: 1, output_tokens: 1, [key]: value}})))])("invalid API data %#", async value => {
  reply(value); await expect(query(config, "token", "hi", [])).rejects.toThrow("Invalid model response");
});
