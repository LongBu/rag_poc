import {bytes, record, validPrompt, type Exchange} from "./data";

export class HistoryCleared extends Error {}

export class HistoryStore {
  readonly key: string;
  readonly epochKey: string;
  private epoch: string | null = null;
  private snapshot: string | null = null;
  constructor(issuer: string, subject: string) {
    this.key = `bedrock-chat:${encodeURIComponent(issuer)}:${subject}`;
    this.epochKey = `${this.key}:generation`;
  }
  async load(): Promise<Exchange[]> {
    return navigator.locks.request(this.key, () => {
      this.epoch = localStorage.getItem(this.epochKey);
      if (this.epoch === null) {
        this.epoch = crypto.randomUUID();
        localStorage.setItem(this.epochKey, this.epoch);
      }
      const raw = localStorage.getItem(this.key);
      if (raw === null) {this.snapshot = null; return [];}
      if (bytes(raw) > 1024**2) throw new Error("Saved history exceeds its size limit.");
      const data: unknown = JSON.parse(raw);
      if (!record(data) || data.version !== 1 || !Array.isArray(data.exchanges) || data.exchanges.length > 100
          || !data.exchanges.every((pair: unknown) => record(pair) && typeof pair.user === "string" && validPrompt(pair.user)
            && typeof pair.assistant === "string" && pair.assistant.trim().length > 0 && pair.assistant.isWellFormed()
            && typeof pair.timestamp === "number" && Number.isFinite(pair.timestamp) && pair.timestamp >= 0)) throw new Error("Saved history is invalid or unsupported.");
      this.snapshot = raw;
      return data.exchanges as Exchange[];
    });
  }
  async save(exchanges: Exchange[]): Promise<{exchanges: Exchange[]; removed: number}> {
    return navigator.locks.request(this.key, () => {
      if (localStorage.getItem(this.epochKey) !== this.epoch) throw new HistoryCleared("Conversation was cleared in another tab.");
      if (localStorage.getItem(this.key) !== this.snapshot) throw new Error("Saved history changed in another tab.");
      const retained = exchanges.slice(-100);
      let raw = JSON.stringify({version: 1, exchanges: retained});
      while (bytes(raw) > 1024**2) {
        retained.shift();
        raw = JSON.stringify({version: 1, exchanges: retained});
      }
      localStorage.setItem(this.key, raw);
      this.snapshot = raw;
      return {exchanges: retained, removed: exchanges.length - retained.length};
    });
  }
  async clear(): Promise<void> {
    await navigator.locks.request(this.key, () => {
      // An epoch also invalidates pending responses in tabs whose history was already empty.
      this.epoch = crypto.randomUUID();
      try { localStorage.setItem(this.epochKey, this.epoch); }
      finally { localStorage.removeItem(this.key); this.snapshot = null; }
    });
  }
}
