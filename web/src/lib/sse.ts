/**
 * SSE client with auto-reconnect.
 *
 * Usage:
 *   const sse = getSSE();
 *   sse.on("world.snapshot", (payload: WorldSnapshot) => { ... });
 *   sse.on("cost.tick", (payload: CostTickPayload) => { ... });
 *   // cleanup:
 *   sse.off("world.snapshot", handler);
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type SSEHandler = (payload: any) => void;

export class SkyHerdSSE {
  private url: string;
  private handlers: Map<string, SSEHandler[]> = new Map();
  private es: EventSource | null = null;
  private reconnectDelay = 1000;
  private maxDelay = 30000;
  private closed = false;

  constructor(url: string = "/events") {
    this.url = url;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on(eventType: string, handler: (payload: any) => void): this {
    const list = this.handlers.get(eventType) ?? [];
    list.push(handler);
    this.handlers.set(eventType, list);
    return this;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  off(eventType: string, handler: (payload: any) => void): void {
    const list = this.handlers.get(eventType) ?? [];
    this.handlers.set(
      eventType,
      list.filter((h) => h !== handler),
    );
  }

  connect(): this {
    this.closed = false;
    this._open();
    return this;
  }

  close(): void {
    this.closed = true;
    this.es?.close();
    this.es = null;
  }

  private _open(): void {
    if (this.closed) return;

    const es = new EventSource(this.url);
    this.es = es;

    const eventTypes = [
      "world.snapshot",
      "cost.tick",
      "attest.append",
      "agent.log",
      "fence.breach",
      "drone.update",
    ];

    for (const type of eventTypes) {
      es.addEventListener(type, (e: MessageEvent) => {
        try {
          const payload = JSON.parse(e.data);
          const handlers = this.handlers.get(type) ?? [];
          for (const h of handlers) h(payload);
        } catch {
          // Malformed JSON — ignore
        }
      });
    }

    es.addEventListener("message", (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data);
        const handlers = this.handlers.get("message") ?? [];
        for (const h of handlers) h(payload);
      } catch {
        // ignore
      }
    });

    es.onerror = () => {
      es.close();
      this.es = null;
      if (!this.closed) {
        setTimeout(() => {
          this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxDelay);
          this._open();
        }, this.reconnectDelay);
      }
    };

    es.onopen = () => {
      this.reconnectDelay = 1000;
    };
  }
}

/** Global singleton SSE client */
let _globalSSE: SkyHerdSSE | null = null;

export function getSSE(): SkyHerdSSE {
  if (!_globalSSE) {
    _globalSSE = new SkyHerdSSE("/events");
    _globalSSE.connect();
  }
  return _globalSSE;
}
