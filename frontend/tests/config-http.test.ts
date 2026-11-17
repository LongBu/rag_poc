/** @jest-environment-options {"url":"http://localhost/"} */
import {loadConfig} from "../src/data";
import {config} from "./fixtures";

test("rejects an insecure page even when the API origin matches", async () => {
  global.fetch = jest.fn().mockResolvedValue({ok: true, json: async () => config});
  await expect(loadConfig()).rejects.toThrow("Invalid configuration");
});
