import {useEffect, useRef, useState, type FormEvent} from "react";
import type {User, UserManager} from "oidc-client-ts";
import {context, query, validPrompt, type Config, type Exchange, type Usage} from "./data";
import {signOut, validUser} from "./auth";
import {HistoryCleared, HistoryStore} from "./history";

export function App({config, auth, initialUser, initialNotice}: {config: Config; auth: UserManager; initialUser: User | null; initialNotice: string}) {
  const [user, setUser] = useState(initialUser);
  const [messages, setMessages] = useState<Exchange[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [restoring, setRestoring] = useState(initialUser !== null);
  const [notice, setNotice] = useState(initialNotice);
  const [usage, setUsage] = useState<Usage | null>(null);
  const generation = useRef(0);
  const inFlight = useRef(false);
  const store = useRef<HistoryStore | null>(null);
  const transcript = useRef<HTMLDivElement>(null);
  const nearBottom = useRef(true);
  const selected = context(messages, draft);

  useEffect(() => {
    if (user === null) return;
    let active = true;
    const history = new HistoryStore(config.issuer, user.profile.sub);
    function restore(history: HistoryStore, failureNotice: string) {
      const version = generation.current;
      store.current = history;
      setRestoring(true);
      void history.load().then(saved => {
        if (active && version === generation.current) setMessages(saved);
      }).catch(() => {
        if (active && version === generation.current) {
          store.current = null;
          setNotice(failureNotice);
        }
      }).finally(() => {if (active && version === generation.current) setRestoring(false);});
    }
    restore(history, "Saved history could not be restored. Continuing in memory.");
    const removed = (event: StorageEvent) => {
      if (event.key === null || event.key === history.epochKey || (event.key === history.key && event.newValue === null)) {
        generation.current++;
        inFlight.current = false;
        setPending(false);
        setMessages([]);
        setDraft("");
        setUsage(null);
        setNotice("Conversation cleared in another tab.");
        restore(new HistoryStore(config.issuer, user.profile.sub), "Saved history unavailable. Clear Chrome site data if erasure failed.");
      }
    };
    const expired = () => {
      generation.current++;
      inFlight.current = false;
      setPending(false);
      setUsage(null);
      store.current = null;
      setMessages([]);
      setDraft("");
      setUser(null);
      setNotice("Sign in again to continue.");
    };
    window.addEventListener("storage", removed);
    auth.events.addAccessTokenExpired(expired);
    return () => {
      active = false;
      generation.current++;
      window.removeEventListener("storage", removed);
      auth.events.removeAccessTokenExpired(expired);
    };
  }, [user, config, auth]);

  useEffect(() => {
    if (transcript.current && nearBottom.current) transcript.current.scrollTop = transcript.current.scrollHeight;
  }, [messages, pending]);

  async function clear() {
    generation.current++;
    inFlight.current = false;
    setPending(false);
    setRestoring(false);
    setMessages([]);
    setDraft("");
    setUsage(null);
    try {
      await (store.current ?? new HistoryStore(config.issuer, config.ownerSub)).clear();
      setNotice("Conversation cleared.");
      return true;
    } catch {
      store.current = null;
      setNotice("Saved history could not be erased. Clear this site's data in Chrome settings.");
      return false;
    }
  }

  async function logout() {
    const erased = await clear();
    setUser(null);
    if (!erased) window.alert("Saved history could not be erased. Clear this site's data in Chrome settings.");
    try { await signOut(auth, config); }
    catch { setNotice("Local session ended. Hosted sign-out failed; close this tab or try signing out again."); }
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    if (restoring || inFlight.current || !validPrompt(draft)) return;
    if (!validUser(user, config)) {
      setUser(null);
      setNotice("Sign in again to continue.");
      return;
    }
    inFlight.current = true;
    setPending(true);
    setNotice("");
    const version = generation.current;
    const prompt = draft;
    try {
      const result = await query(config, user.access_token, prompt, selected.history);
      if (version !== generation.current) return;
      let next = [...messages, {user: prompt, assistant: result.text, timestamp: Date.now()}];
      if (store.current) {
        try {
          const saved = await store.current.save(next);
          next = saved.exchanges;
          if (saved.removed > 0) setNotice(`${saved.removed} older exchanges removed by the storage retention limit.`);
        } catch (error) {
          if (error instanceof HistoryCleared) {
            setMessages([]);
            setDraft("");
            setUsage(null);
            store.current = null;
            setNotice("Conversation cleared in another tab. Continuing in memory.");
            return;
          }
          setNotice("History could not be saved. Continuing in memory; another tab may have changed it, or Chrome storage is unavailable.");
        }
      }
      if (version !== generation.current) return;
      setMessages(next);
      setUsage(result.usage);
      setDraft(current => current === prompt ? "" : current);
    } catch {
      if (version === generation.current) setNotice("Request failed. Check your login, connection, access, or quota. Your draft is kept for deliberate retry.");
    } finally {
      if (version === generation.current) {inFlight.current = false; setPending(false);}
    }
  }

  async function copy(text: string) {
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(text);
      setNotice("Answer copied.");
    } catch { setNotice("Copy failed. Select the answer text and copy it manually."); }
  }

  return <main>
    <header><h1>Private Bedrock chat</h1><div className="controls"><button onClick={() => void clear()}>Clear conversation</button><button onClick={() => void logout()}>Sign out</button></div></header>
    <p>Answers use the model and conversation context only. They are not verified against live sources.</p>
    <p className="privacy">Saved messages survive browser restarts on this device. Same-origin scripts and anyone with access to your unlocked browser profile can read them. Clear conversation or sign out to erase them.</p>
    <p role="status" aria-live="polite">{notice}</p>
    {user === null ? <section><p>Sign in as the configured owner to ask a question.</p><button onClick={() => {void auth.signinRedirect().catch(() => setNotice("Sign-in failed. Check browser storage and try again."));}}>Sign in</button></section> : <>
      <div className="transcript" role="log" aria-label="Conversation" ref={transcript} onScroll={event => {const el = event.currentTarget; nearBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;}}>
        {restoring && <p role="status">Restoring saved conversation…</p>}
        {messages.map((pair, index) => <article key={`${pair.timestamp}:${index}`}><h2>You</h2><p>{pair.user}</p><h2>Assistant</h2><p>{pair.assistant}</p><button onClick={() => void copy(pair.assistant)}>Copy answer</button></article>)}
        {pending && <p role="status">Waiting for the complete answer…</p>}
      </div>
      {usage && <p>Tokens: {usage.input_tokens} input, {usage.output_tokens} output.</p>}
      {selected.omitted > 0 && <p>{selected.omitted} older exchanges excluded from model context; saved messages are kept separately.</p>}
      <form onSubmit={event => void submit(event)}><label htmlFor="prompt">Your question</label><textarea id="prompt" disabled={restoring} value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={event => {
        if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) {event.preventDefault(); void submit();}
      }}/><p>Enter submits. Shift+Enter adds a newline. Maximum 4,000 characters.</p><button type="submit" disabled={restoring || pending || !validPrompt(draft)}>Submit</button></form>
    </>}
  </main>;
}
