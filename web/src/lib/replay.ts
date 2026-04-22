/**
 * Replay driver — demo mode substitute for SkyHerdSSE.
 *
 * Loads /replay.json on mount, cycles through all scenarios end-to-end,
 * re-emitting each event through the same handler map that SkyHerdSSE uses.
 * Events play at ~3× speed so judges see action within a few seconds.
 *
 * Interface is intentionally compatible with SkyHerdSSE so callers that do
 *   sse.on("fence.breach", handler)
 * work unchanged regardless of which driver is active.
 */

import type { SSEHandler } from "./sse";

// Speed multiplier: 3× means a 600 s scenario plays in ~200 s.
const SPEED = 3;

interface ReplayEvent {
  ts_rel: number;
  kind: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload: Record<string, any>;
}

interface ReplayScenario {
  name: string;
  duration_s: number;
  events: ReplayEvent[];
}

interface ReplayBundle {
  scenarios: ReplayScenario[];
}

export class SkyHerdReplay {
  private handlers: Map<string, SSEHandler[]> = new Map();
  private stopped = false;
  private timeouts: ReturnType<typeof setTimeout>[] = [];

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
    this.stopped = false;
    this._start().catch(() => {
      // Non-fatal — replay.json may be unavailable in local dev
    });
    return this;
  }

  close(): void {
    this.stopped = true;
    for (const t of this.timeouts) clearTimeout(t);
    this.timeouts = [];
  }

  private _emit(kind: string, payload: unknown): void {
    if (this.stopped) return;
    const handlers = this.handlers.get(kind) ?? [];
    for (const h of handlers) h(payload);
  }

  private async _start(): Promise<void> {
    let bundle: ReplayBundle;
    try {
      const resp = await fetch("/replay.json");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      bundle = await resp.json();
    } catch (err) {
      console.warn("[SkyHerdReplay] Failed to load /replay.json:", err);
      return;
    }

    if (this.stopped) return;

    // Play all scenarios end-to-end in a loop
    let cumulativeOffsetMs = 0;

    const enqueueScenario = (scenario: ReplayScenario, offsetMs: number): number => {
      let lastTsRel = 0;
      for (const ev of scenario.events) {
        const wallMs = offsetMs + (ev.ts_rel / SPEED) * 1000;
        lastTsRel = ev.ts_rel;
        const t = setTimeout(() => {
          // Emit under original event kind + also emit as "agent.log" for any
          // kind not natively understood by the dashboard so something shows up.
          this._emit(ev.kind, ev.payload);

          // For kinds that the dashboard expects, also synthesise compatible events:
          if (ev.kind === "fence.breach") {
            this._emit("agent.log", {
              agent: "FenceLineDispatcher",
              state: "active",
              msg: `Fence breach — ${ev.payload.species_hint ?? "unknown"} at ${ev.payload.fence_id ?? "fence"}`,
              ts: Date.now() / 1000,
            });
          } else if (ev.kind === "health.check") {
            this._emit("agent.log", {
              agent: "HerdHealthWatcher",
              state: "active",
              msg: `Health alert — cow ${ev.payload.cow_tag}: ${(ev.payload.disease_flags ?? []).join(", ")}`,
              ts: Date.now() / 1000,
            });
          } else if (ev.kind === "calving.prelabor") {
            this._emit("agent.log", {
              agent: "CalvingWatch",
              state: "active",
              msg: `Pre-labor — cow ${ev.payload.cow_tag}, confidence ${ev.payload.confidence}`,
              ts: Date.now() / 1000,
            });
          } else if (ev.kind === "storm.warning" || ev.kind === "weather.storm") {
            this._emit("agent.log", {
              agent: "GrazingOptimizer",
              state: "active",
              msg: `Storm ETA ${Math.round((ev.payload.eta_s ?? 0) / 60)} min — herd move recommended`,
              ts: Date.now() / 1000,
            });
          } else if (ev.kind === "drone.flyover_complete") {
            this._emit("drone.update", {
              ...ev.payload,
              ts: Date.now() / 1000,
            });
          }
        }, wallMs);
        this.timeouts.push(t);
      }
      // Return wall-ms at which this scenario ends
      return offsetMs + (lastTsRel / SPEED) * 1000;
    };

    // Schedule all scenarios back-to-back with a 2 s gap between them
    for (const scenario of bundle.scenarios) {
      cumulativeOffsetMs = enqueueScenario(scenario, cumulativeOffsetMs) + 2000;
    }

    // Restart from beginning once all scenarios have played
    const totalMs = cumulativeOffsetMs;
    const loopTimer = setTimeout(() => {
      if (!this.stopped) {
        this.close();
        this.stopped = false;
        this._start().catch(() => {});
      }
    }, totalMs + 1000);
    this.timeouts.push(loopTimer);
  }
}

let _globalReplay: SkyHerdReplay | null = null;

export function getReplay(): SkyHerdReplay {
  if (!_globalReplay) {
    _globalReplay = new SkyHerdReplay();
    _globalReplay.connect();
  }
  return _globalReplay;
}
