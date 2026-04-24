/**
 * Replay driver — demo mode substitute for SkyHerdSSE.
 *
 * Loads /replay.json on start(), cycles through all scenarios end-to-end,
 * re-emitting each event through the same handler map that SkyHerdSSE uses.
 * Events play at ~3× speed so judges see action within a few seconds.
 *
 * Interface is intentionally compatible with SkyHerdSSE so callers that do
 *   sse.on("fence.breach", handler)
 * work unchanged regardless of which driver is active.
 *
 * Opt-in start (Phase 3.1): a fresh instance is paused — nothing flows until
 * the user clicks "Start Simulation". pause() halts emission by dropping all
 * pending timers; a subsequent start() restarts the full sequence from
 * scenario 0. (Simpler than tracking per-event resumption — the demo is
 * short enough that a full re-run is acceptable.)
 *
 * Ambient synthesiser: replay.json only contains scenario-specific events
 * (fence.breach, water.low, etc.). The live FastAPI server also emits
 * world.snapshot / attest.append / memory.written / agent.log at a steady
 * cadence — which is what drives RanchMap cows, the ledger counter, the
 * memory panel, and the agent-lane flashes. We mirror that cadence here so
 * the static-hosted demo shows the same density of activity as local.
 */

import type { SSEHandler } from "./sse";

// Internal speed multiplier baseline: 3× compresses a 600 s scenario to
// ~200 s of wall time. The UI exposes this as "1×"; choosing "2×" in the UI
// sets the internal multiplier to 6×.
const DEFAULT_SPEED = 3;

// Agent identities — same names as the live mesh.
const AGENTS = [
  "FenceLineDispatcher",
  "HerdHealthWatcher",
  "PredatorPatternLearner",
  "GrazingOptimizer",
  "CalvingWatch",
] as const;

type AgentName = (typeof AGENTS)[number];

// Rotating-chatter messages per agent — what judges see streaming through
// AgentLanes and ScenarioStrip.
const AGENT_MESSAGES: Record<AgentName, readonly string[]> = {
  FenceLineDispatcher: [
    "scanning fence NE segment",
    "LoRaWAN telemetry nominal",
    "evaluating intrusion probability",
    "drone armed and ready",
    "fence integrity check passed",
    "thermal signature review",
  ],
  HerdHealthWatcher: [
    "checking cow BCS across herd",
    "gait analysis complete — 98 cows nominal",
    "ocular discharge flagged on cow 042",
    "temperature reading within range",
    "pulling cow 017 for vet review",
    "drafting vet intake packet",
  ],
  PredatorPatternLearner: [
    "analyzing thermal track log",
    "coyote path confidence 0.72",
    "cross-referencing multi-night patterns",
    "crossing prediction — NE fence 04:20",
    "hand-off to FenceLineDispatcher",
    "updated predator heatmap",
  ],
  GrazingOptimizer: [
    "forage map updated",
    "recommending rotation paddock-3 → paddock-5",
    "weather window evaluated",
    "herd move plan drafted",
    "acoustic nudge scheduled",
    "paddock utilization balanced",
  ],
  CalvingWatch: [
    "monitoring 3 cows in calving window",
    "pre-labor signal from cow 018",
    "dystocia risk nominal",
    "priority page to rancher queued",
    "calving pen status green",
    "birth recorded — cow 041, live calf",
  ],
};

// Ranch coordinate frame — RanchMap uses normalized [0..1] coords for both
// paddock bounds and entity positions (see RanchMap fallback). Keep every
// value in that range.
const RANCH_BOUNDS = { x_min: 0.04, x_max: 0.96, y_min: 0.04, y_max: 0.96 };

// 4-quadrant split matching ranch_a.yaml (p_nw / p_ne / p_sw / p_se).
const AMBIENT_PADDOCKS = [
  { id: "north", bounds: [0, 0, 0.5, 0.5] as [number, number, number, number], forage_pct: 72 },
  { id: "south", bounds: [0.5, 0, 1, 0.5] as [number, number, number, number], forage_pct: 58 },
  { id: "east", bounds: [0.5, 0.5, 1, 1] as [number, number, number, number], forage_pct: 84 },
  { id: "west", bounds: [0, 0.5, 0.5, 1] as [number, number, number, number], forage_pct: 43 },
];

const AMBIENT_TANKS = [
  { id: "wt_n", pos: [0.5, 0.18] as [number, number], level_pct: 82 },
  { id: "wt_s", pos: [0.5, 0.82] as [number, number], level_pct: 64 },
];

function hex(len: number): string {
  const chars = "0123456789abcdef";
  let out = "";
  for (let i = 0; i < len; i += 1) out += chars[Math.floor(Math.random() * 16)];
  return out;
}

function pick<T>(arr: readonly T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

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

interface AmbientCow {
  id: string;
  tag: string;
  pos: [number, number];
  state: "healthy" | "watch" | "sick" | "calving";
  bcs: number;
}

// Drone patrol waypoints (normalized [0..1]). Figure-8 through the ranch
// so the drone visits every quadrant instead of circling forever.
const DRONE_WAYPOINTS: [number, number][] = [
  [0.15, 0.2],   // SW corner
  [0.38, 0.35],  // interior west
  [0.5, 0.12],   // S midpoint
  [0.82, 0.2],   // SE corner
  [0.68, 0.42],  // interior south
  [0.88, 0.55],  // E midpoint
  [0.82, 0.82],  // NE corner
  [0.55, 0.72],  // interior east
  [0.5, 0.9],    // N midpoint
  [0.18, 0.82],  // NW corner
  [0.32, 0.6],   // interior north
  [0.12, 0.5],   // W midpoint
];

export class SkyHerdReplay {
  private handlers: Map<string, SSEHandler[]> = new Map();
  private paused = true;
  private timeouts: ReturnType<typeof setTimeout>[] = [];
  private intervals: ReturnType<typeof setInterval>[] = [];

  // UI "1×" maps to this internal multiplier. Mutated by setSpeed().
  private speed = DEFAULT_SPEED;

  // Ambient synthesiser state — persists across pause/start so the world
  // doesn't reset to pristine on every resume.
  private ambientSeq = 0;
  private ambientCost = 0;
  private ambientLogIdx = 0;
  private ambientAgentIdx = 0;
  private ambientCows: AmbientCow[] | null = null;

  // Drone patrol state — waypoint-to-waypoint with eased travel + a small
  // perpendicular wobble so the path doesn't look mechanical.
  private droneLegIdx = 0;
  private droneLegStartMs = 0;

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

  /**
   * SkyHerdSSE-compatible: callers may still invoke connect(). In replay mode
   * this is now a no-op so the driver only runs after an explicit start().
   */
  connect(): this {
    return this;
  }

  /**
   * Kick off playback from scenario 0. If already running, ignored.
   * Safe to call after pause() to resume (restarts the sequence).
   */
  start(): this {
    if (!this.paused) return this;
    this.paused = false;
    // Wake existing subscribers (StatBand "READY → LIVE", scenario strip, etc.)
    // even before the fetch resolves — keeps the UI in sync with the click.
    this._emit("scenario.active", {
      name: "coyote",
      pass_idx: 0,
      speed: this.speed,
      started_at: new Date().toISOString(),
    });

    // Populate the map immediately so the click feels responsive.
    this._emitWorldSnapshot();
    this._startAmbient();

    this._run().catch(() => {
      // Non-fatal — replay.json may be unavailable in local dev.
    });
    return this;
  }

  /** Halt emission and cancel all pending event timers. */
  pause(): this {
    this.paused = true;
    for (const t of this.timeouts) clearTimeout(t);
    this.timeouts = [];
    for (const i of this.intervals) clearInterval(i);
    this.intervals = [];
    return this;
  }

  isPaused(): boolean {
    return this.paused;
  }

  getSpeed(): number {
    return this.speed;
  }

  /**
   * Set the playback speed (internal scalar; UI exposes 0.5× = 1.5, 1× = 3,
   * 2× = 6, 4× = 12). While running, restarts ambient intervals so their
   * cadence matches. Scenario event timing is frozen at schedule-time, so
   * new speeds take full effect on the next loop iteration.
   */
  setSpeed(speed: number): this {
    this.speed = Math.max(0.25, speed);
    if (!this.paused) {
      for (const i of this.intervals) clearInterval(i);
      this.intervals = [];
      this._startAmbient();
    }
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

  private _seedCows(): AmbientCow[] {
    const cows: AmbientCow[] = [];
    const count = 14;
    for (let i = 0; i < count; i += 1) {
      const x = RANCH_BOUNDS.x_min + Math.random() * (RANCH_BOUNDS.x_max - RANCH_BOUNDS.x_min);
      const y = RANCH_BOUNDS.y_min + Math.random() * (RANCH_BOUNDS.y_max - RANCH_BOUNDS.y_min);
      const roll = Math.random();
      const state: AmbientCow["state"] =
        roll > 0.94 ? "sick" : roll > 0.88 ? "calving" : roll > 0.8 ? "watch" : "healthy";
      cows.push({
        id: `cow_${String(i + 1).padStart(3, "0")}`,
        tag: String(i + 1).padStart(3, "0"),
        pos: [x, y],
        state,
        bcs: 4 + Math.random() * 2,
      });
    }
    return cows;
  }

  /** Drift cows + orbit drone, then emit a world.snapshot. */
  private _emitWorldSnapshot(): void {
    if (!this.ambientCows) this.ambientCows = this._seedCows();
    // Brownian drift: each cow wanders ~0.4% of the map per tick.
    for (const cow of this.ambientCows) {
      const dx = (Math.random() - 0.5) * 0.008;
      const dy = (Math.random() - 0.5) * 0.008;
      cow.pos = [
        Math.max(RANCH_BOUNDS.x_min, Math.min(RANCH_BOUNDS.x_max, cow.pos[0] + dx)),
        Math.max(RANCH_BOUNDS.y_min, Math.min(RANCH_BOUNDS.y_max, cow.pos[1] + dy)),
      ];
    }

    // Waypoint patrol: ease between DRONE_WAYPOINTS, ~5 s per leg at 1×.
    const now = Date.now();
    const LEG_MS = 5000 * (DEFAULT_SPEED / this.speed);
    if (this.droneLegStartMs === 0) this.droneLegStartMs = now;
    if (now - this.droneLegStartMs >= LEG_MS) {
      this.droneLegIdx = (this.droneLegIdx + 1) % DRONE_WAYPOINTS.length;
      this.droneLegStartMs = now;
    }
    const from = DRONE_WAYPOINTS[this.droneLegIdx];
    const to = DRONE_WAYPOINTS[(this.droneLegIdx + 1) % DRONE_WAYPOINTS.length];
    const t = Math.min(1, (now - this.droneLegStartMs) / LEG_MS);
    // Ease-in-out cubic so the drone accelerates/decelerates at waypoints.
    const easeT = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    // Perpendicular bank so the path isn't a straight line — gives the
    // drone a subtle S-curve between waypoints.
    const dx = to[0] - from[0];
    const dy = to[1] - from[1];
    const perpX = -dy;
    const perpY = dx;
    const bank = Math.sin(easeT * Math.PI) * 0.035;
    const drone = {
      pos: [
        from[0] + dx * easeT + perpX * bank,
        from[1] + dy * easeT + perpY * bank,
      ] as [number, number],
      state: "patrolling",
      battery_pct: Math.round(70 + 20 * Math.sin(now / 60_000)),
      alt_m: 35 + Math.round(8 * Math.sin(now / 4200)),
    };

    this._emit("world.snapshot", {
      cows: this.ambientCows,
      predators: [],
      drone,
      paddocks: AMBIENT_PADDOCKS,
      water_tanks: AMBIENT_TANKS,
      is_night: false,
      weather: { conditions: "clear", temp_f: 68, wind_kt: 4 },
    });
  }

  private _startAmbient(): void {
    // Scale every ambient cadence by current speed — at 1× (speed=3) the
    // factor is 1.0; faster speeds shrink the interval proportionally.
    const k = DEFAULT_SPEED / this.speed;

    // world.snapshot — 700ms wall (mirrors live 2 s / 3× playback)
    this.intervals.push(
      setInterval(() => this._emitWorldSnapshot(), 700 * k),
    );

    // cost.tick — 1.2 s wall, monotonically increasing total so the ticker animates
    this.intervals.push(
      setInterval(() => {
        if (this.paused) return;
        this.ambientCost += 0.00032;
        this._emit("cost.tick", {
          total_usd_spent: this.ambientCost,
          total_usd: this.ambientCost,
          cost_usd_hr: 0.17,
        });
      }, 1200 * k),
    );

    // attest.append — 1.1 s wall, incrementing seq so the LEDGER counter climbs
    this.intervals.push(
      setInterval(() => {
        if (this.paused) return;
        this.ambientSeq += 1;
        const agent = AGENTS[this.ambientAgentIdx % AGENTS.length];
        this.ambientAgentIdx += 1;
        this._emit("attest.append", {
          seq: this.ambientSeq,
          hash_hex: hex(64),
          prev_hash_hex: hex(64),
          kind: "agent_tool_call",
          agent,
          ts: Date.now() / 1000,
        });
      }, 1100 * k),
    );

    // memory.written — 2 s wall (MemoryPanel rows flash in)
    this.intervals.push(
      setInterval(() => {
        if (this.paused) return;
        const agent = pick(AGENTS);
        this._emit("memory.written", {
          agent,
          memory_id: `mem_${hex(8)}`,
          memory_version_id: `ver_${hex(12)}`,
          memory_store_id: "local",
          path: `/patterns/${agent.toLowerCase()}/${hex(4)}`,
          content_sha256: hex(64),
        });
      }, 2000 * k),
    );

    // agent.log — 380ms wall, rotating across all 5 agents
    this.intervals.push(
      setInterval(() => {
        if (this.paused) return;
        const agent = AGENTS[this.ambientLogIdx % AGENTS.length];
        this.ambientLogIdx += 1;
        const messages = AGENT_MESSAGES[agent];
        this._emit("agent.log", {
          agent,
          message: pick(messages),
          ts: Date.now() / 1000,
          state: "active",
          level: "INFO",
        });
      }, 380 * k),
    );
  }

  private async _run(): Promise<void> {
    let bundle: ReplayBundle;
    try {
      const resp = await fetch("/replay.json");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      bundle = await resp.json();
    } catch {
      // Non-fatal — ambient emitters keep the dashboard alive without it.
      return;
    }

    if (this.paused) return;

    // Play all scenarios end-to-end in a loop
    let cumulativeOffsetMs = 0;

    const enqueueScenario = (scenario: ReplayScenario, offsetMs: number): number => {
      let lastTsRel = 0;
      // Announce the scenario as it opens.
      const activeAt = setTimeout(() => {
        this._emit("scenario.active", {
          name: scenario.name,
          pass_idx: 0,
          speed: this.speed,
          started_at: new Date().toISOString(),
        });
      }, offsetMs);
      this.timeouts.push(activeAt);

      for (const ev of scenario.events) {
        const wallMs = offsetMs + (ev.ts_rel / this.speed) * 1000;
        lastTsRel = ev.ts_rel;
        const t = setTimeout(() => {
          // Emit under original event kind + also synthesise compatible
          // agent.log / drone.update / attest.append payloads so the
          // corresponding dashboard panels react.
          this._emit(ev.kind, ev.payload);

          if (ev.kind === "fence.breach") {
            this._emit("agent.log", {
              agent: "FenceLineDispatcher",
              state: "active",
              level: "WARN",
              message: `fence breach — ${ev.payload.species_hint ?? "unknown"} at ${ev.payload.fence_id ?? "fence"}`,
              ts: Date.now() / 1000,
            });
          } else if (ev.kind === "health.check") {
            this._emit("agent.log", {
              agent: "HerdHealthWatcher",
              state: "active",
              level: "WARN",
              message: `health alert — cow ${ev.payload.cow_tag}: ${(ev.payload.disease_flags ?? []).join(", ")}`,
              ts: Date.now() / 1000,
            });
          } else if (ev.kind === "calving.prelabor") {
            this._emit("agent.log", {
              agent: "CalvingWatch",
              state: "active",
              level: "WARN",
              message: `pre-labor — cow ${ev.payload.cow_tag}, confidence ${ev.payload.confidence}`,
              ts: Date.now() / 1000,
            });
          } else if (ev.kind === "storm.warning" || ev.kind === "weather.storm") {
            this._emit("agent.log", {
              agent: "GrazingOptimizer",
              state: "active",
              level: "WARN",
              message: `storm ETA ${Math.round((ev.payload.eta_s ?? 0) / 60)} min — herd move recommended`,
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

      // Scenario-end beacon (3 s after the last event).
      const endMs = offsetMs + (lastTsRel / this.speed) * 1000 + 3000;
      const endedAt = setTimeout(() => {
        this._emit("scenario.ended", { name: scenario.name });
      }, endMs);
      this.timeouts.push(endedAt);
      return endMs;
    };

    // Schedule all scenarios back-to-back with a 2 s gap between them
    for (const scenario of bundle.scenarios) {
      cumulativeOffsetMs = enqueueScenario(scenario, cumulativeOffsetMs) + 2000;
    }

    // Restart from beginning once all scenarios have played
    const totalMs = cumulativeOffsetMs;
    const loopTimer = setTimeout(() => {
      if (!this.paused) {
        // Clear pending scenario timers (not ambient intervals) and re-run.
        for (const t of this.timeouts) clearTimeout(t);
        this.timeouts = [];
        this._run().catch(() => {});
      }
    }, totalMs + 1000);
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
