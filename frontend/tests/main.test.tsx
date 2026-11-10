import {waitFor} from "@testing-library/react";
import {config, user} from "./fixtures";
jest.mock("../src/data", () => ({loadConfig: jest.fn()}));
jest.mock("../src/auth", () => ({captureCallback: jest.fn(), clearTransient: jest.fn(), finishCallback: jest.fn(), manager: jest.fn()}));
jest.mock("../src/App", () => ({App: jest.fn(() => null)}));
jest.mock("react-dom/client", () => ({createRoot: jest.fn()}));
beforeEach(() => {jest.resetModules(); document.body.innerHTML='<div id="root"></div>';});
function mocks() {
  const data = require("../src/data") as {loadConfig: jest.Mock};
  const auth = require("../src/auth") as {captureCallback: jest.Mock; clearTransient: jest.Mock; finishCallback: jest.Mock; manager: jest.Mock};
  const dom = require("react-dom/client") as {createRoot: jest.Mock};
  const render = jest.fn(); dom.createRoot.mockReturnValue({render});
  data.loadConfig.mockResolvedValue(config); auth.captureCallback.mockReturnValue(null); auth.manager.mockReturnValue({}); auth.finishCallback.mockResolvedValue(null);
  return {data, auth, dom, render};
}
test("entry point renders anonymous and authenticated sessions", async () => {
  const {auth, render, data} = mocks(); const owner=user(); auth.finishCallback.mockResolvedValue(owner); auth.captureCallback.mockReturnValue("http://localhost/?code=private");
  require("../src/main"); await waitFor(()=>expect(render).toHaveBeenCalled());
  const props=render.mock.calls[0][0].props;
  expect(props.initialUser).toBe(owner); expect(props.initialNotice).toBe("");
  expect(auth.captureCallback.mock.invocationCallOrder[0]).toBeLessThan(data.loadConfig.mock.invocationCallOrder[0]);
});
test("entry callback failure renders only sanitized feedback", async () => {
  const {auth, render}=mocks(); auth.finishCallback.mockRejectedValue(new Error("private code state"));
  require("../src/main"); await waitFor(()=>expect(render).toHaveBeenCalled());
  expect(render.mock.calls[0][0].props.initialUser).toBeNull();
  expect(render.mock.calls[0][0].props.initialNotice).toBe("Sign-in failed. Please sign in again.");
});
test.each([false,true])("entry config failure clears transient data even if storage is blocked: %s", async blocked => {
  const {data,auth}=mocks(); data.loadConfig.mockRejectedValue(new Error("private"));
  if(blocked)auth.clearTransient.mockImplementation(()=>{throw new Error("blocked");});
  require("../src/main"); await waitFor(()=>expect(document.getElementById("root")!.textContent).toContain("configuration or browser storage is unavailable"));
  expect(auth.clearTransient).toHaveBeenCalled(); expect(document.body.textContent).not.toContain("private");
});
