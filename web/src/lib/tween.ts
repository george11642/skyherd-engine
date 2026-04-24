/**
 * tween.ts — Pure math + state helpers for the shared RAF tween pipeline.
 *
 * All entities on the ranch map (cows, drone, predators, trail points) share
 * one RAF loop and use `TweenState` records to interpolate between SSE
 * `world.snapshot` ticks. Keeping the math in this module lets vitest cover
 * the eased transitions with mocked `performance.now()` clocks.
 *
 * `prefers-reduced-motion: reduce` → callers should skip the tween entirely
 * (set display = target, fades = 1). This module exposes `prefersReducedMotion`
 * as the single probe.
 */

/** Clamp a value to [lo, hi] — inline-small to avoid an import hop. */
function clamp(v: number, lo: number, hi: number): number {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

/**
 * Ease-out-cubic: `1 - (1 - t)^3`. Curve that feels natural for position
 * settling — fast at start, gentle decel at target. Input clamped to [0,1].
 */
export function easeOutCubic(t: number): number {
  const c = clamp(t, 0, 1);
  const inv = 1 - c;
  return 1 - inv * inv * inv;
}

/** Linear interpolation. */
export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/**
 * TweenState — immutable record describing a single 1-D tween.
 *
 * `start` and `target` are the eased-value endpoints; `tweenStartMs` is the
 * `performance.now()` at which the tween was seeded; `durationMs` is the
 * total eased duration.  `tweenValue(state, now)` returns the current value.
 */
export interface TweenState {
  readonly start: number;
  readonly target: number;
  readonly tweenStartMs: number;
  readonly durationMs: number;
}

export function createTween(
  start: number,
  target: number,
  nowMs: number,
  durationMs: number,
): TweenState {
  return { start, target, tweenStartMs: nowMs, durationMs };
}

/**
 * Current eased value of the tween at `nowMs`.  Before the start time it
 * returns `start`; after completion it returns `target`; otherwise it
 * interpolates with `easeOutCubic`.  `durationMs <= 0` is treated as an
 * instant snap to `target`.
 */
export function tweenValue(state: TweenState, nowMs: number): number {
  if (state.durationMs <= 0) return state.target;
  const raw = (nowMs - state.tweenStartMs) / state.durationMs;
  if (raw <= 0) return state.start;
  if (raw >= 1) return state.target;
  return lerp(state.start, state.target, easeOutCubic(raw));
}

/**
 * Retarget a tween mid-flight: the new tween starts at the CURRENT eased
 * value and heads toward the new target over `newDurationMs` (defaults to
 * the existing `durationMs`). This is what avoids position "jumps" when a
 * new SSE snapshot arrives before the previous tween completed.
 */
export function retarget(
  state: TweenState,
  newTarget: number,
  nowMs: number,
  newDurationMs?: number,
): TweenState {
  return {
    start: tweenValue(state, nowMs),
    target: newTarget,
    tweenStartMs: nowMs,
    durationMs: newDurationMs ?? state.durationMs,
  };
}

/**
 * Linear RGB interpolation, returning an `rgba(...)` string for canvas
 * fillStyle / strokeStyle assignment. Channels are rounded to integers;
 * alpha is pass-through.
 */
export function lerpRgb(
  from: readonly [number, number, number],
  to: readonly [number, number, number],
  t: number,
  alpha: number,
): string {
  const c = clamp(t, 0, 1);
  const r = Math.round(lerp(from[0], to[0], c));
  const g = Math.round(lerp(from[1], to[1], c));
  const b = Math.round(lerp(from[2], to[2], c));
  return `rgba(${r},${g},${b},${alpha})`;
}

/**
 * Safe probe for `prefers-reduced-motion: reduce`. Returns `false` when
 * `window.matchMedia` is unavailable (older jsdom, SSR).
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  if (typeof window.matchMedia !== "function") return false;
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}
