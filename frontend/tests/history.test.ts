import {HistoryCleared, HistoryStore} from "../src/history";
import {config, locks, pair} from "./fixtures";
beforeEach(() => {localStorage.clear(); locks();});
const store = () => new HistoryStore(config.tenantId, config.ownerObjectId);
test("owner-separated restore and erasure", async () => {
  const first = store(); expect(await first.load()).toEqual([]);
  await first.save([pair]);
  expect(await store().load()).toEqual([pair]);
  expect(await new HistoryStore(config.tenantId, "other").load()).toEqual([]);
  expect(await new HistoryStore("other", config.ownerObjectId).load()).toEqual([]);
  await first.clear(); expect(localStorage.getItem(first.key)).toBeNull();
  expect(await first.load()).toEqual([]);
});
test("stale tabs cannot restore cleared history, including empty history", async () => {
  const first = store(), stale = store();
  await first.load(); await stale.load(); await first.clear();
  await expect(stale.save([pair])).rejects.toBeInstanceOf(HistoryCleared);
  await stale.load(); await stale.save([pair]); expect(await first.load()).toEqual([pair]);
});
test("retention bounds", async () => {
  const history = store(); await history.load();
  const pairs = Array.from({length: 101}, (_, timestamp) => ({...pair, timestamp}));
  expect(await history.save(pairs)).toEqual({exchanges: pairs.slice(1), removed: 1});
  const big = {...pair, assistant: "😀".repeat(150000)};
  expect((await history.save([big, {...big, timestamp: 2}])).removed).toBe(1);
  expect((await history.save([{...pair, assistant: "x".repeat(1024**2)}])).exchanges).toEqual([]);
});
test.each([{initial: []}, {initial: [pair]}])("stale saves preserve another tab's exchanges: $initial", async ({initial}) => {
  const first = store(), stale = store();
  await first.load(); await first.save(initial); await stale.load();
  const next = {...pair, user: "another tab", timestamp: 2};
  await first.save([...initial, next]);
  await expect(stale.save([...initial, {...pair, user: "stale tab"}])).rejects.toThrow("changed in another tab");
  expect(await store().load()).toEqual([...initial, next]);
  await stale.clear();
  await stale.save([pair]);
  expect(await store().load()).toEqual([pair]);
});
test.each(["{", "null", JSON.stringify({version: 2, exchanges: []}), JSON.stringify({version: 1, exchanges: null}),
  JSON.stringify({version: 1, exchanges: Array(101).fill(pair)}),
  ...[null, {...pair, user: 1}, {...pair, user: ""}, {...pair, assistant: 1}, {...pair, assistant: " "}, {...pair, assistant: "\ud800"}, {...pair, timestamp: "bad"}, {...pair, timestamp: -1}].map(value => JSON.stringify({version: 1, exchanges: [value]})),
  '{"version":1,"exchanges":[{"user":"ok","assistant":"ok","timestamp":1e400}]}',
  "x".repeat(1024**2+1),
])("reject invalid storage %#", async raw => {
  const history = store(); localStorage.setItem(history.key, raw);
  await expect(history.load()).rejects.toThrow();
});
test("quota, unavailable storage, and failed erasure are not reported as success", async () => {
  const history = store(); await history.load();
  const set = jest.spyOn(Storage.prototype, "setItem").mockImplementation(() => {throw new Error("quota");});
  await expect(history.save([pair])).rejects.toThrow("quota");
  const remove = jest.spyOn(Storage.prototype, "removeItem");
  await expect(history.clear()).rejects.toThrow("quota"); expect(remove).toHaveBeenCalledWith(history.key);
  set.mockRestore(); remove.mockRestore();
  jest.spyOn(Storage.prototype, "getItem").mockImplementation(() => {throw new Error("blocked");});
  await expect(history.load()).rejects.toThrow("blocked");
  jest.restoreAllMocks();
});
test("Azure namespace does not adopt provider history and uses the same lock for load/save/clear", async () => {
  const history = store();
  const legacyKey = `bedrock-chat:${encodeURIComponent(config.issuer)}:${config.ownerObjectId}`;
  const awsKey = `bedrock-chat:${encodeURIComponent("https://cognito-idp.us-east-1.amazonaws.com/synthetic")}:${config.ownerObjectId}`;
  const raw = JSON.stringify({version: 1, exchanges: [pair]});
  for (const key of [legacyKey, awsKey]) localStorage.setItem(key, raw);
  expect(history.key).toBe(`azure-chat:${config.tenantId}:${config.ownerObjectId}`);
  expect(await history.load()).toEqual([]);
  await history.save([pair]); await history.clear();
  expect(jest.mocked(navigator.locks.request).mock.calls.map(call => call[0])).toEqual([history.key, history.key, history.key]);
  for (const key of [legacyKey, awsKey]) expect(localStorage.getItem(key)).toBe(raw);
});
