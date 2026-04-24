import { getSSE } from "@/lib/sse";

const STORAGE_KEY = "skyherd:audioMuted";
const GAIN_CEILING = 0.15;
const ATTEST_DEBOUNCE_MS = 350;

class AudioController {
  private ctx: AudioContext | null = null;
  private muted: boolean;
  private resumed = false;
  private lastAttestTick = 0;

  constructor() {
    const stored = localStorage.getItem(STORAGE_KEY);
    this.muted = stored === "true";
  }

  resume(): void {
    if (this.resumed) return;
    this.resumed = true;
    const ctx = this._getContext();
    ctx.resume().catch(() => {});
    this._subscribe();
  }

  setMuted(muted: boolean): void {
    this.muted = muted;
    localStorage.setItem(STORAGE_KEY, String(muted));
  }

  isMuted(): boolean {
    return this.muted;
  }

  private _getContext(): AudioContext {
    if (!this.ctx) {
      this.ctx = new AudioContext();
    }
    return this.ctx;
  }

  private _play(fn: (ctx: AudioContext) => void): void {
    if (this.muted) return;
    const ctx = this._getContext();
    if (ctx.state === "suspended") return;
    fn(ctx);
  }

  private _tone(
    ctx: AudioContext,
    type: OscillatorType,
    freqStart: number,
    freqEnd: number,
    durationSec: number,
    gain: number,
  ): void {
    const osc = ctx.createOscillator();
    const gainNode = ctx.createGain();
    osc.type = type;
    osc.connect(gainNode);
    gainNode.connect(ctx.destination);

    const now = ctx.currentTime;
    osc.frequency.setValueAtTime(freqStart, now);
    if (freqEnd !== freqStart) {
      osc.frequency.linearRampToValueAtTime(freqEnd, now + durationSec);
    }
    gainNode.gain.setValueAtTime(Math.min(gain, GAIN_CEILING), now);
    gainNode.gain.exponentialRampToValueAtTime(0.001, now + durationSec);

    osc.start(now);
    osc.stop(now + durationSec);
  }

  private _playFenceBreach(): void {
    this._play((ctx) => {
      this._tone(ctx, "triangle", 440, 220, 0.12, GAIN_CEILING);
    });
  }

  private _playScenarioActive(): void {
    this._play((ctx) => {
      this._tone(ctx, "sine", 660, 660, 0.25, 0.1);
    });
  }

  private _playScenarioEnded(): void {
    this._play((ctx) => {
      this._tone(ctx, "sine", 440, 330, 0.2, 0.08);
    });
  }

  private _playAttestAppend(): void {
    const now = Date.now();
    if (now - this.lastAttestTick < ATTEST_DEBOUNCE_MS) return;
    this.lastAttestTick = now;
    this._play((ctx) => {
      this._tone(ctx, "sine", 1200, 1200, 0.02, 0.03);
    });
  }

  private _playWaterLow(): void {
    this._play((ctx) => {
      const now = ctx.currentTime;
      const osc1 = ctx.createOscillator();
      const g1 = ctx.createGain();
      osc1.type = "square";
      osc1.frequency.value = 800;
      osc1.connect(g1);
      g1.connect(ctx.destination);
      g1.gain.setValueAtTime(0.08, now);
      g1.gain.exponentialRampToValueAtTime(0.001, now + 0.06);
      osc1.start(now);
      osc1.stop(now + 0.06);

      const osc2 = ctx.createOscillator();
      const g2 = ctx.createGain();
      osc2.type = "square";
      osc2.frequency.value = 800;
      osc2.connect(g2);
      g2.connect(ctx.destination);
      const t2 = now + 0.14;
      g2.gain.setValueAtTime(0.08, t2);
      g2.gain.exponentialRampToValueAtTime(0.001, t2 + 0.06);
      osc2.start(t2);
      osc2.stop(t2 + 0.06);
    });
  }

  private _playDeterrent(): void {
    this._play((ctx) => {
      this._tone(ctx, "sine", 600, 1200, 0.18, 0.1);
    });
  }

  private _subscribe(): void {
    const sse = getSSE();
    sse.on("fence.breach", () => this._playFenceBreach());
    sse.on("scenario.active", () => this._playScenarioActive());
    sse.on("scenario.ended", () => this._playScenarioEnded());
    sse.on("attest.append", () => this._playAttestAppend());
    sse.on("water.low", () => this._playWaterLow());
    sse.on("agent.log", (payload: { message?: string }) => {
      const msg = (payload?.message ?? "").toLowerCase();
      if (msg.includes("deterrent") || msg.includes("acoustic")) {
        this._playDeterrent();
      }
    });
  }
}

let _instance: AudioController | null = null;

export function getAudio(): AudioController {
  if (!_instance) {
    _instance = new AudioController();
  }
  return _instance;
}
