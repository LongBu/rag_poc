import {act, fireEvent, render, screen, waitFor} from "@testing-library/react";
import type {User, UserManager} from "oidc-client-ts";
import {App} from "../src/App";
import * as data from "../src/data";
import * as authModule from "../src/auth";
import {HistoryCleared, HistoryStore} from "../src/history";
import {config, locks, pair, user} from "./fixtures";

const answer = {text: "answer text", usage: {input_tokens: 10, output_tokens: 2}};
function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {resolve=yes; reject=no;});
  return {promise, resolve, reject};
}
async function setup(owner: User | null = user()) {
  const auth = {signinRedirect: jest.fn().mockResolvedValue(undefined), events: {addAccessTokenExpired: jest.fn(), removeAccessTokenExpired: jest.fn()}} as unknown as UserManager;
  const view = render(<App config={config} auth={auth} initialUser={owner} initialNotice="initial notice"/>);
  await act(async () => {});
  return {auth, ...view};
}
function submit(prompt="question") {
  fireEvent.change(screen.getByLabelText("Your question"), {target: {value: prompt}});
  fireEvent.click(screen.getByRole("button", {name: "Submit"}));
}
async function saved(pairs=[pair]) {
  const store = new HistoryStore(config.issuer, config.ownerSub);
  await store.load(); await store.save(pairs);
  return store;
}
beforeEach(() => {
  localStorage.clear(); sessionStorage.clear(); locks();
  jest.spyOn(data, "query").mockResolvedValue(answer);
  jest.spyOn(authModule, "signOut").mockResolvedValue();
});
afterEach(() => jest.restoreAllMocks());

test("login and safe failure", async () => {
  const {auth} = await setup(null);
  expect(screen.queryByLabelText("Your question")).toBeNull();
  jest.mocked(auth.signinRedirect).mockRejectedValue(new Error("private"));
  fireEvent.click(screen.getByRole("button", {name: "Sign in"}));
  expect(await screen.findByText(/Sign-in failed/)).toBeInTheDocument();
  expect(screen.queryByText("private")).toBeNull();
  fireEvent.click(screen.getByRole("button", {name: "Clear conversation"}));
  expect(await screen.findByText("Conversation cleared.")).toBeInTheDocument();
});
test("submit, loading, usage, context payload and exact copy", async () => {
  const pending = deferred<data.Answer>(); jest.mocked(data.query).mockReturnValue(pending.promise);
  await setup(); submit("hello");
  expect(screen.getByRole("button", {name: "Submit"})).toBeDisabled();
  expect(screen.getByText(/Waiting for the complete answer/)).toBeInTheDocument();
  fireEvent.keyDown(screen.getByLabelText("Your question"), {key: "Enter"});
  expect(data.query).toHaveBeenCalledTimes(1);
  await act(async () => pending.resolve(answer));
  expect(screen.getByText("hello")).toBeInTheDocument();
  expect(screen.getByText("answer text")).toBeInTheDocument();
  expect(screen.getByText("Tokens: 10 input, 2 output.")).toBeInTheDocument();
  expect(data.query).toHaveBeenCalledWith(config, "synthetic", "hello", []);
  const copied = deferred<void>(); const writeText = jest.fn().mockReturnValue(copied.promise);
  Object.defineProperty(navigator, "clipboard", {configurable:true, value:{writeText}});
  fireEvent.click(screen.getByRole("button", {name:"Copy answer"}));
  expect(screen.queryByText("Answer copied.")).toBeNull();
  await act(async () => copied.resolve());
  expect(screen.getByText("Answer copied.")).toBeInTheDocument();
  expect(writeText).toHaveBeenCalledWith("answer text"); expect(data.query).toHaveBeenCalledTimes(1);
});
test.each([undefined, {}, {writeText: jest.fn().mockRejectedValue(new Error("private"))}])("copy fallback %#", async clipboard => {
  await saved(); await setup(); Object.defineProperty(navigator, "clipboard", {configurable:true,value:clipboard});
  fireEvent.click(screen.getByRole("button", {name:"Copy answer"}));
  expect(await screen.findByText(/Select the answer text/)).toBeInTheDocument(); expect(data.query).not.toHaveBeenCalled();
});
test("restore, inert HTML, context notice, and scroll intent", async () => {
  const pairs = Array.from({length:11}, (_, timestamp) => ({user:`question ${timestamp}`, assistant:`<img src=x onerror=alert(1)> ${timestamp}`, timestamp}));
  await saved(pairs); await setup();
  expect(screen.getByText(pairs[0].assistant)).toBeInTheDocument(); expect(screen.queryByRole("img")).toBeNull();
  expect(screen.getByText(/1 older exchanges excluded/)).toBeInTheDocument();
  const transcript = screen.getByRole("log");
  Object.defineProperties(transcript, {scrollHeight:{configurable:true,value:1000},clientHeight:{configurable:true,value:100}});
  transcript.scrollTop=0; fireEvent.scroll(transcript); submit();
  await screen.findByText("answer text"); expect(transcript.scrollTop).toBe(0);
  expect(jest.mocked(data.query).mock.calls[0][3]).toHaveLength(10);
  transcript.scrollTop=950; fireEvent.scroll(transcript); submit("next");
  await waitFor(() => expect(screen.getAllByText("answer text")).toHaveLength(2));
  expect(transcript.scrollTop).toBe(1000);
});
test("Enter, newline, IME, invalid drafts, and duplicate guards", async () => {
  const pending = deferred<data.Answer>(); jest.mocked(data.query).mockReturnValue(pending.promise);
  await setup(); const input=screen.getByLabelText("Your question");
  fireEvent.keyDown(input,{key:"Enter"}); expect(data.query).not.toHaveBeenCalled();
  fireEvent.change(input,{target:{value:"hello\nworld"}});
  fireEvent.keyDown(input,{key:"Enter",shiftKey:true});
  fireEvent.keyDown(input,{key:"Enter",isComposing:true});
  fireEvent.keyDown(input,{key:"Enter",keyCode:229});
  fireEvent.keyDown(input,{key:"a"}); expect(data.query).not.toHaveBeenCalled();
  fireEvent.keyDown(input,{key:"Enter"}); fireEvent.submit(input.closest("form")!);
  expect(data.query).toHaveBeenCalledTimes(1);
  await act(async () => pending.resolve(answer));
});
test("expired credentials cannot query", async () => {
  await setup(Object.assign(user(),{expires_at:1}));
  submit(); expect(await screen.findByText("Sign in again to continue.")).toBeInTheDocument(); expect(data.query).not.toHaveBeenCalled();
});
test("expiry event clears private UI but preserves saved messages", async () => {
  const store=await saved(); const {auth}=await setup();
  const expire=jest.mocked(auth.events.addAccessTokenExpired).mock.calls[0][0];
  act(() => expire());
  expect(screen.queryByText("answer")).toBeNull(); expect(localStorage.getItem(store.key)).not.toBeNull();
});
test("logout after expiry erases the owner's saved messages", async () => {
  const store=await saved(); const {auth}=await setup();
  act(()=>jest.mocked(auth.events.addAccessTokenExpired).mock.calls[0][0]());
  fireEvent.click(screen.getByRole("button",{name:"Sign out"}));
  await waitFor(()=>expect(authModule.signOut).toHaveBeenCalled());
  expect(localStorage.getItem(store.key)).toBeNull();
});
test("clear before sign-in erases saved owner history", async () => {
  const store=await saved(); await setup(null);
  fireEvent.click(screen.getByRole("button",{name:"Clear conversation"}));
  await screen.findByText("Conversation cleared.");
  expect(localStorage.getItem(store.key)).toBeNull();
});
test("failed erasure can be retried after storage recovers", async () => {
  const store=await saved(); await setup();
  const remove=jest.spyOn(Storage.prototype,"removeItem").mockImplementationOnce(()=>{throw new Error("blocked");});
  fireEvent.click(screen.getByRole("button",{name:"Clear conversation"}));
  await screen.findByText(/Saved history could not be erased/);
  expect(localStorage.getItem(store.key)).not.toBeNull();
  fireEvent.click(screen.getByRole("button",{name:"Clear conversation"}));
  await screen.findByText("Conversation cleared.");
  expect(localStorage.getItem(store.key)).toBeNull(); expect(remove).toHaveBeenCalledTimes(2);
});
test("submission waits for restoration and retains earlier exchanges", async () => {
  const store=await saved(); const restored=deferred<void>(); const load=HistoryStore.prototype.load;
  jest.spyOn(HistoryStore.prototype,"load").mockImplementation(function(this: HistoryStore){return load.call(this).then(saved=>restored.promise.then(()=>saved));});
  await setup(); const input=screen.getByLabelText("Your question");
  expect(input).toBeDisabled(); expect(screen.getByRole("button",{name:"Submit"})).toBeDisabled();
  fireEvent.change(input,{target:{value:"new question"}});
  fireEvent.keyDown(input,{key:"Enter"}); fireEvent.submit(input.closest("form")!);
  expect(data.query).not.toHaveBeenCalled();
  await act(async()=>restored.resolve());
  expect(input).toBeEnabled(); submit("new question");
  await screen.findByText("answer text");
  expect(data.query).toHaveBeenCalledWith(config,"synthetic","new question",[{user:pair.user,assistant:pair.assistant}]);
  expect(JSON.parse(localStorage.getItem(store.key)!).exchanges).toHaveLength(2);
});
test("failed restoration allows memory-only chat without overwriting saved history", async () => {
  const store=await saved();
  jest.spyOn(HistoryStore.prototype,"load").mockRejectedValue(new Error("temporarily unavailable"));
  await setup(); submit("new question"); await screen.findByText("answer text");
  expect(JSON.parse(localStorage.getItem(store.key)!).exchanges).toEqual([pair]);
});
test("an arriving answer preserves a newer unsent draft", async () => {
  const response=deferred<data.Answer>(); jest.mocked(data.query).mockReturnValue(response.promise);
  await setup(); submit("first question");
  fireEvent.change(screen.getByLabelText("Your question"),{target:{value:"unsent follow-up"}});
  await act(async()=>response.resolve(answer));
  expect(screen.getByLabelText("Your question")).toHaveValue("unsent follow-up");
  expect(data.query).toHaveBeenCalledTimes(1);
});
test("failed request keeps draft for deliberate retry", async () => {
  jest.mocked(data.query).mockRejectedValue(new Error("private")); await setup(); submit("keep this");
  expect(await screen.findByText(/Your draft is kept/)).toBeInTheDocument();
  expect(screen.getByLabelText("Your question")).toHaveValue("keep this"); expect(screen.queryByText("private")).toBeNull();
});
test.each([false,true])("late success/error cannot restore after clear: %s", async failure => {
  const pending=deferred<data.Answer>(); jest.mocked(data.query).mockReturnValue(pending.promise); await setup(); submit();
  fireEvent.click(screen.getByRole("button",{name:"Clear conversation"}));
  await screen.findByText("Conversation cleared.");
  await act(async () => {if(failure) pending.reject(new Error("private")); else pending.resolve(answer);});
  expect(screen.queryByText("answer text")).toBeNull(); expect(screen.queryByText(/Request failed/)).toBeNull();
});
test("clearing during persistence cannot restore a late response", async () => {
  const pending=deferred<{exchanges:data.Exchange[];removed:number}>();
  jest.spyOn(HistoryStore.prototype,"save").mockReturnValue(pending.promise); await setup(); submit();
  await waitFor(()=>expect(HistoryStore.prototype.save).toHaveBeenCalled());
  fireEvent.click(screen.getByRole("button",{name:"Clear conversation"})); await screen.findByText("Conversation cleared.");
  await act(async()=>pending.resolve({exchanges:[pair],removed:0})); expect(screen.queryByText("answer")).toBeNull();
});
test("retention notice and persistence failure", async () => {
  const save=jest.spyOn(HistoryStore.prototype,"save").mockResolvedValue({exchanges:[pair],removed:1}); await setup(); submit();
  expect(await screen.findByText(/storage retention limit/)).toBeInTheDocument();
  save.mockRejectedValue(new Error("quota")); submit("next");
  expect(await screen.findByText(/History could not be saved/)).toBeInTheDocument(); expect(screen.getByText("answer text")).toBeInTheDocument();
});
test("epoch mismatch rejects stale messages before storage event arrives", async () => {
  jest.spyOn(HistoryStore.prototype,"save").mockRejectedValue(new HistoryCleared()); await setup(); submit();
  expect(await screen.findByText(/Conversation cleared in another tab. Continuing/)).toBeInTheDocument(); expect(screen.queryByText("answer text")).toBeNull();
  submit("fresh"); expect(await screen.findByText("answer text")).toBeInTheDocument();
});
test("a conflicting tab's saved history survives while new answers stay in memory", async () => {
  const other = await saved(); await setup();
  const elsewhere = {...pair, user: "other tab question", timestamp: 2};
  await other.save([pair, elsewhere]);
  submit();
  expect(await screen.findByText(/History could not be saved/)).toBeInTheDocument();
  expect(screen.getByText("answer text")).toBeInTheDocument();
  submit("follow-up");
  await waitFor(()=>expect(screen.getAllByText("answer text")).toHaveLength(2));
  expect(await new HistoryStore(config.issuer, config.ownerSub).load()).toEqual([pair, elsewhere]);
});
test.each([null,"epoch","removed"])("cross-tab removal invalidates pending response %s", async kind => {
  const history=await saved(); const pending=deferred<data.Answer>(); jest.mocked(data.query).mockReturnValue(pending.promise); await setup(); submit();
  await act(async()=>{window.dispatchEvent(new StorageEvent("storage",{key:kind===null?null:kind==="epoch"?history.epochKey:history.key,newValue:null}));});
  expect(screen.getByText("Conversation cleared in another tab.")).toBeInTheDocument();
  await act(async()=>pending.resolve(answer)); expect(screen.queryByText("answer text")).toBeNull();
});
test("unrelated storage events do not clear history", async () => {
  const history=await saved(); await setup();
  act(()=>{window.dispatchEvent(new StorageEvent("storage",{key:"other",newValue:null}));window.dispatchEvent(new StorageEvent("storage",{key:history.key,newValue:"updated"}));});
  expect(screen.getByText("answer")).toBeInTheDocument();
});
test("cross-tab refresh waits for and adopts history saved after a clear", async () => {
  const other = await saved(); await setup();
  await other.clear();
  const fresh = {...pair, user: "saved after clear", timestamp: 2};
  await other.save([fresh]);
  const gate = deferred<void>(), load = HistoryStore.prototype.load;
  jest.spyOn(HistoryStore.prototype,"load").mockImplementation(function(this: HistoryStore) {
    return gate.promise.then(()=>load.call(this));
  });
  act(()=>window.dispatchEvent(new StorageEvent("storage",{key:other.epochKey})));
  const input = screen.getByLabelText("Your question");
  expect(input).toBeDisabled();
  fireEvent.change(input,{target:{value:"next question"}});
  fireEvent.submit(input.closest("form")!);
  expect(data.query).not.toHaveBeenCalled();
  await act(async()=>gate.resolve());
  expect(screen.getByText("saved after clear")).toBeInTheDocument();
  submit("next question");
  await screen.findByText("answer text");
  expect(data.query).toHaveBeenCalledWith(config,"synthetic","next question",[{user:fresh.user,assistant:fresh.assistant}]);
  expect(JSON.parse(localStorage.getItem(other.key)!).exchanges.map((p:data.Exchange)=>p.user)).toEqual(["saved after clear","next question"]);
});
test.each([false,true])("superseded refresh cannot update a newer refresh: failure=%s", async failure => {
  await setup();
  const first=deferred<data.Exchange[]>(), second=deferred<data.Exchange[]>();
  jest.spyOn(HistoryStore.prototype,"load").mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
  act(()=>window.dispatchEvent(new StorageEvent("storage",{key:null})));
  act(()=>window.dispatchEvent(new StorageEvent("storage",{key:null})));
  await act(async()=>{if(failure)first.reject(new Error("old failure"));else first.resolve([pair]);});
  expect(screen.getByLabelText("Your question")).toBeDisabled();
  expect(screen.queryByText("answer")).toBeNull();
  expect(screen.queryByText(/Saved history unavailable/)).toBeNull();
  await act(async()=>second.resolve([]));
  expect(screen.getByLabelText("Your question")).toBeEnabled();
});
test.each(["Clear conversation","Sign out"])("pending refresh cannot undo %s", async action => {
  await setup();
  const pending=deferred<data.Exchange[]>();
  jest.spyOn(HistoryStore.prototype,"load").mockReturnValue(pending.promise);
  act(()=>window.dispatchEvent(new StorageEvent("storage",{key:null})));
  fireEvent.click(screen.getByRole("button",{name:action}));
  await waitFor(()=>expect(screen.queryByText("Restoring saved conversation…")).toBeNull());
  await act(async()=>pending.resolve([pair]));
  expect(screen.queryByText("answer")).toBeNull();
  if(action==="Clear conversation") expect(screen.getByLabelText("Your question")).toBeEnabled();
  else expect(authModule.signOut).toHaveBeenCalled();
});
test("storage failure during logout remains visible before hosted navigation", async () => {
  await setup(); jest.spyOn(HistoryStore.prototype,"clear").mockRejectedValue(new Error("blocked"));
  const alert=jest.spyOn(window,"alert").mockImplementation(()=>{});
  fireEvent.click(screen.getByRole("button",{name:"Clear conversation"}));
  expect(await screen.findByText(/Saved history could not be erased/)).toBeInTheDocument();
  // Reopening the authenticated view restores its store; logout also handles failed erasure.
  const view=render(<App config={config} auth={{events:{addAccessTokenExpired:jest.fn(),removeAccessTokenExpired:jest.fn()}} as unknown as UserManager} initialUser={user()} initialNotice=""/>);
  await act(async()=>{});
  fireEvent.click(view.getAllByRole("button",{name:"Sign out"})[1]);
  await waitFor(()=>expect(alert).toHaveBeenCalled()); expect(authModule.signOut).toHaveBeenCalled();
});
test("logout, hosted failure, and clearing an unauthenticated view", async () => {
  jest.mocked(authModule.signOut).mockRejectedValue(new Error("private")); await saved(); await setup();
  fireEvent.click(screen.getByRole("button",{name:"Sign out"}));
  expect(await screen.findByText(/Hosted sign-out failed/)).toBeInTheDocument(); expect(screen.queryByText("answer")).toBeNull();
  fireEvent.click(screen.getByRole("button",{name:"Clear conversation"})); await screen.findByText("Conversation cleared.");
});
test.each([false,true])("late history load does not restore after unmount: %s", async failure => {
  const pending=deferred<data.Exchange[]>(); jest.spyOn(HistoryStore.prototype,"load").mockReturnValue(pending.promise);
  const view=await setup(); view.unmount();
  await act(async()=>{if(failure)pending.reject(new Error("blocked"));else pending.resolve([pair]);});
});
test("late initial history load cannot undo clear", async () => {
  const pending=deferred<data.Exchange[]>(); jest.spyOn(HistoryStore.prototype,"load").mockReturnValue(pending.promise);
  await setup(); fireEvent.click(screen.getByRole("button",{name:"Clear conversation"})); await screen.findByText("Conversation cleared.");
  await act(async()=>pending.resolve([pair])); expect(screen.queryByText("answer")).toBeNull();
});
test("failed restore and cross-tab refresh continue in memory", async () => {
  jest.spyOn(HistoryStore.prototype,"load").mockRejectedValue(new Error("blocked")); await setup();
  expect(screen.getByText(/could not be restored/)).toBeInTheDocument();
  await act(async()=>{window.dispatchEvent(new StorageEvent("storage",{key:null}));});
  expect(screen.getByText(/Saved history unavailable/)).toBeInTheDocument(); submit();
  expect(await screen.findByText("answer text")).toBeInTheDocument();
});
test.each([false,true])("cross-tab refresh resolving after unmount is ignored: %s", async failure => {
  const view=await setup(); const pending=deferred<data.Exchange[]>(); jest.spyOn(HistoryStore.prototype,"load").mockReturnValue(pending.promise);
  act(()=>{window.dispatchEvent(new StorageEvent("storage",{key:null}));}); view.unmount();
  await act(async()=>{if(failure)pending.reject(new Error("blocked"));else pending.resolve([]);});
});
