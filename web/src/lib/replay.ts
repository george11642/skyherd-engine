/**
 * Replay driver — demo mode substitute for SkyHerdSSE.
 *
 * Loads /replay.v2.json on start() — a faithful capture of every event the
 * real Python simulator's EventBroadcaster emitted during a single end-to-end
 * run (5 scenarios × ~600 events each): world.snapshot, cost.tick,
 * attest.append, agent.log, vet_intake.drafted, scenario.active/ended, and
 * every scenario-specific trigger. Every cow position, every drone waypoint,
 * every ledger hash, every agent message comes from the real sim at seed=42.
 *
 * NO client-side synthesis. The only transform is coordinate normalization:
 * the Python world places cows in meters (ranch_a bounds 2000×2000), but
 * RanchMap expects [0..1]. We divide on load.
 *
 * Interface is intentionally compatible with SkyHerdSSE so callers that do
 *   sse.on("fence.breach", handler)
 * work unchanged regardless of which driver is active.
 *
 * Opt-in start (Phase 3.1): a fresh instance is paused — nothing flows until
 * the user clicks "Start Simulation". pause() halts emission by dropping all
 * pending timers; a subsequent start() restarts the full sequence from
 * scenario 0.
 */

import type { SSEHandler } from "./sse";

// Internal speed multiplier baseline: 3× compresses a 600 s scenario to
// ~200 s of wall time. UI "1×" = this default; "2×" → 6, etc.
const DEFAULT_SPEED = 3;

// ranch_a.yaml bounds_m = [2000, 2000]. Cow/predator positions in the
// captured world.snapshot stream are in meters with origin at SW corner.
// RanchMap expects [0..1] for everything.
const WORLD_BOUNDS_M = 2000;

interface ReplayEvent {
  ts_rel: number;
  kind: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload: Record<string, any>;
}

interface ReplayScenario {
  name: string;
  duration_s: number;
  event_count?: number;
  events: ReplayEvent[];
}

interface ReplayBundle {
  version?: number;
  generated_at?: string;
  seed?: number;
  git_sha?: string;
  scenarios: ReplayScenario[];
}

/**
 * Rescale captured payloads into the dashboard's normalized coord system.
 * - world.snapshot.cows[].pos: meters → [0..1]
 * - world.snapshot.predators[].pos: meters → [0..1]
 * - world.snapshot.water_tanks (absent from capture — RanchMap has fallback)
 * Drone position is already normalized by the capture script.
 */
function normalizePayload(kind: string, payload: Record<string, unknown>): Record<string, unknown> {
  if (kind !== "world.snapshot") return payload;
  const out = { ...payload };
  const cows = payload.cows as Array<Record<string, unknown>> | undefined;
  if (Array.isArray(cows)) {
    out.cows = cows.map((c) => {
      const pos = c.pos as [number, number] | undefined;
      if (!pos) return c;
      return { ...c, pos: [pos[0] / WORLD_BOUNDS_M, pos[1] / WORLD_BOUNDS_M] };
    });
  }
  const preds = payload.predators as Array<Record<string, unknown>> | undefined;
  if (Array.isArray(preds)) {
    out.predators = preds.map((p) => {
      const pos = p.pos as [number, number] | undefined;
      if (!pos) return p;
      return { ...p, pos: [pos[0] / WORLD_BOUNDS_M, pos[1] / WORLD_BOUNDS_M] };
    });
  }
  return out;
}

export class SkyHerdReplay {
  private handlers: Map<string, SSEHandler[]> = new Map();
  private paused = true;
  private timeouts: ReturnType<typeof setTimeout>[] = [];

  // UI "1×" maps to this internal multiplier. Mutated by setSpeed().
  private speed = DEFAULT_SPEED;

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

  /** SkyHerdSSE-compat: no-op in replay mode; driver starts on explicit start(). */
  connect(): this {
    return this;
  }

  start(): this {
    if (!this.paused) return this;
    this.paused = false;
    // Prime the UI (StatBand READY → LIVE, ScenarioStrip auto-advance) before
    // the fetch resolves.
    this._emit("scenario.active", {
      name: "coyote",
      pass_idx: 0,
      speed: this.speed,
      started_at: new Date().toISOString(),
    });
    this._run().catch(() => {
      // Non-fatal — replay.v2.json may be unavailable in local dev.
    });
    return this;
  }

  pause(): this {
    this.paused = true;
    for (const t of this.timeouts) clearTimeout(t);
    this.timeouts = [];
    return this;
  }

  isPaused(): boolean {
    return this.paused;
  }

  getSpeed(): number {
    return this.speed;
  }

  /**
   * Set playback speed (UI 0.5×/1×/2×/4× → internal 1.5/3/6/12).
   * While running, new speeds take full effect on the next loop iteration.
   */
  setSpeed(speed: number): this {
    this.speed = Math.max(0.25, speed);
    return this;
  }

  /** Alias kept for SkyHerdSSE compatibility — close() == pause(). */
  close(): void {
    this.pause();
  }

  private _emit(kind: string, payload: unknown): void {
    if (this.paused) return;
    const handlers = this.handlers.get(kind) ?? [];
    for (const h of handlers) h(payload);
  }

  private async _run(): Promise<void> {
    let bundle: ReplayBundle;
    try {
      const resp = await fetch("/replay.v2.json");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      bundle = await resp.json();
    } catch {
      // Non-fatal — no ambient fallback. Dashboard will remain empty.
      return;
    }

    if (this.paused) return;

    let cumulativeOffsetMs = 0;

    const enqueueScenario = (scenario: ReplayScenario, offsetMs: number): number => {
      let lastTsRel = 0;
      for (const ev of scenario.events) {
        const wallMs = offsetMs + (ev.ts_rel / this.speed) * 1000;
        lastTsRel = ev.ts_rel;
        const payload = normalizePayload(ev.kind, ev.payload);
        const t = setTimeout(() => {
          this._emit(ev.kind, payload);
        }, wallMs);
        this.timeouts.push(t);
      }
      return offsetMs + (lastTsRel / this.speed) * 1000;
    };

    for (const scenario of bundle.scenarios) {
      cumulativeOffsetMs = enqueueScenario(scenario, cumulativeOffsetMs) + 2000;
    }

    // Loop playback — when all scenarios have played, restart.
    const loopTimer = setTimeout(() => {
      if (!this.paused) {
        for (const t of this.timeouts) clearTimeout(t);
        this.timeouts = [];
        this._run().catch(() => {});
      }
    }, cumulativeOffsetMs + 1000);
    this.timeouts.push(loopTimer);
  }
}

let _globalReplay: SkyHerdReplay | null = null;

/**
 * Module-level singleton. Returned instance is paused — callers (e.g. the
 * ScenarioStrip "Start Simulation" button) must invoke `.start()` to begin
 * playback.
 */
export function getReplay(): SkyHerdReplay {
  if (!_globalReplay) {
    _globalReplay = new SkyHerdReplay();
  }
  return _globalReplay;
}

/** Test-only reset. Exposed for vitest so singleton state doesn't leak. */
export function __resetReplayForTest(): void {
  _globalReplay = null;
}
