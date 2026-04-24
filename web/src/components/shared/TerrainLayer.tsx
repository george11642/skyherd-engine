/**
 * TerrainLayer — WebGL2 stylized ranch terrain, rendered beneath RanchMap.
 *
 * Phase 10.5 (DASH10-08). Raw WebGL2, no deps. A single fullscreen triangle
 * vertex shader (clip-space trick, no vertex buffer) plus a 3-octave value-
 * noise fragment shader blending the sage → dust design tokens to hint at
 * landscape texture without being photorealistic.
 *
 * Mounted as a sibling `<canvas>` absolutely positioned behind the existing
 * ranch-map 2D canvas. The parent `<div className="relative w-full h-full">`
 * on RanchMap anchors it.
 *
 * Accessibility: `prefers-reduced-motion: reduce` → time uniform frozen at
 * t=0 (no animation). The draw itself is static at that point, so after the
 * first frame the RAF loop exits.
 *
 * Graceful fallback: if `getContext("webgl2")` returns null, a solid
 * sage-tinted fill is drawn via 2D context so the map still has a backdrop.
 */

import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "@/lib/tween";

// Design-token colors (match index.css sage / dust / bg-0). Normalized to
// floats to match the shader uniform convention.
const SAGE: [number, number, number] = [148 / 255, 176 / 255, 136 / 255];
const DUST: [number, number, number] = [210 / 255, 178 / 255, 138 / 255];
const BG0: [number, number, number] = [10 / 255, 12 / 255, 16 / 255];

// Vertex shader: generates a fullscreen triangle from gl_VertexID alone.
// Draws 3 verts that cover clip space with no buffer upload.
const VS_SRC = `#version 300 es
precision highp float;
out vec2 vUv;
void main() {
  // gl_VertexID: 0, 1, 2 → x/y in { -1, -1 } / { 3, -1 } / { -1, 3 }
  float x = float((gl_VertexID & 1) << 2) - 1.0;
  float y = float((gl_VertexID & 2) << 1) - 1.0;
  vUv = vec2(x * 0.5 + 0.5, 1.0 - (y * 0.5 + 0.5));
  gl_Position = vec4(x, y, 0.0, 1.0);
}`;

// Fragment shader: 3-octave value noise blended into sage→dust gradient,
// darkened toward bg-0 at the edges, with a very slow time warp so the
// ground feels alive. Kept compact — ~80 lines of GLSL.
const FS_SRC = `#version 300 es
precision highp float;
in vec2 vUv;
uniform float uTime;
uniform vec2 uResolution;
uniform vec3 uSage;
uniform vec3 uDust;
uniform vec3 uBg0;
out vec4 fragColor;

// Hash: cheap pseudo-random from 2D position.
float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

// Value noise — smoothstep-interpolated 4-corner hash.
float vnoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

// 3-octave fBm.
float fbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 3; i++) {
    v += a * vnoise(p);
    p *= 2.04;
    a *= 0.5;
  }
  return v;
}

void main() {
  // Scale UV to maintain roughly square noise cells regardless of aspect.
  vec2 p = vUv * uResolution / 120.0;
  // Slow drift so the ground breathes.
  float t = uTime * 0.02;
  float n = fbm(p + vec2(t, -t * 0.6));
  // Secondary noise for subtle highlights.
  float n2 = fbm(p * 2.3 + vec2(-t * 0.3, t * 0.5));

  // Base gradient — sage at top-left, dust at bottom-right.
  float grad = clamp((vUv.x + vUv.y) * 0.5, 0.0, 1.0);
  vec3 base = mix(uSage, uDust, grad);

  // Modulate with noise (light, so we stay in "background" territory).
  vec3 tinted = mix(base * 0.18, base * 0.35, n);
  tinted = mix(tinted, tinted * 1.25, smoothstep(0.55, 0.9, n2));

  // Heavy darken toward bg-0 — this is meant to sit UNDER the 2D canvas.
  // Overall brightness caps at ~20% of the design tokens.
  vec3 color = mix(uBg0, tinted, 0.45);

  // Vignette — subtle darken at the outer edges.
  float r = length(vUv - 0.5);
  float vignette = smoothstep(0.8, 0.4, r);
  color *= mix(0.7, 1.0, vignette);

  fragColor = vec4(color, 1.0);
}`;

function compileShader(
  gl: WebGL2RenderingContext,
  type: number,
  src: string,
): WebGLShader | null {
  const sh = gl.createShader(type);
  if (!sh) return null;
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    // Shader failed to compile — let the fallback path take over.
    gl.deleteShader(sh);
    return null;
  }
  return sh;
}

function linkProgram(
  gl: WebGL2RenderingContext,
  vs: WebGLShader,
  fs: WebGLShader,
): WebGLProgram | null {
  const prog = gl.createProgram();
  if (!prog) return null;
  gl.attachShader(prog, vs);
  gl.attachShader(prog, fs);
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
    gl.deleteProgram(prog);
    return null;
  }
  return prog;
}

function paintFallback(canvas: HTMLCanvasElement): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const w = canvas.width;
  const h = canvas.height;
  const grad = ctx.createLinearGradient(0, 0, w, h);
  grad.addColorStop(0, `rgba(${SAGE.map((c) => Math.round(c * 255 * 0.22)).join(",")},1)`);
  grad.addColorStop(1, `rgba(${DUST.map((c) => Math.round(c * 255 * 0.22)).join(",")},1)`);
  ctx.fillStyle = `rgba(${BG0.map((c) => Math.round(c * 255)).join(",")},1)`;
  ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = grad;
  ctx.globalAlpha = 0.35;
  ctx.fillRect(0, 0, w, h);
  ctx.globalAlpha = 1;
}

export function TerrainLayer() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const glRef = useRef<WebGL2RenderingContext | null>(null);
  const progRef = useRef<WebGLProgram | null>(null);
  const uniformsRef = useRef<{
    time: WebGLUniformLocation | null;
    resolution: WebGLUniformLocation | null;
    sage: WebGLUniformLocation | null;
    dust: WebGLUniformLocation | null;
    bg0: WebGLUniformLocation | null;
  } | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    // Attempt WebGL2 context. Fallback cleanly on failure.
    let gl: WebGL2RenderingContext | null = null;
    try {
      gl = canvas.getContext("webgl2") as WebGL2RenderingContext | null;
    } catch {
      gl = null;
    }

    if (!gl) {
      paintFallback(canvas);
      return undefined;
    }

    const vs = compileShader(gl, gl.VERTEX_SHADER, VS_SRC);
    const fs = compileShader(gl, gl.FRAGMENT_SHADER, FS_SRC);
    if (!vs || !fs) {
      paintFallback(canvas);
      return undefined;
    }

    const prog = linkProgram(gl, vs, fs);
    if (!prog) {
      paintFallback(canvas);
      return undefined;
    }

    glRef.current = gl;
    progRef.current = prog;
    uniformsRef.current = {
      time: gl.getUniformLocation(prog, "uTime"),
      resolution: gl.getUniformLocation(prog, "uResolution"),
      sage: gl.getUniformLocation(prog, "uSage"),
      dust: gl.getUniformLocation(prog, "uDust"),
      bg0: gl.getUniformLocation(prog, "uBg0"),
    };

    // Empty VAO is required in WebGL2 for drawArrays without buffers.
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);

    // Need to capture reduced-motion pref once per mount; listen for changes
    // so the animation pauses if the user toggles the preference at runtime.
    const mql =
      typeof window !== "undefined" && typeof window.matchMedia === "function"
        ? window.matchMedia("(prefers-reduced-motion: reduce)")
        : null;
    let reduceMotion = prefersReducedMotion();
    const onChange = () => {
      reduceMotion = prefersReducedMotion();
      if (!reduceMotion && rafRef.current === 0) {
        rafRef.current = requestAnimationFrame(loop);
      }
    };
    mql?.addEventListener?.("change", onChange);

    const startMs =
      typeof performance !== "undefined" && typeof performance.now === "function"
        ? performance.now()
        : Date.now();
    const draw = (nowMs: number) => {
      const glCtx = glRef.current;
      const program = progRef.current;
      const u = uniformsRef.current;
      if (!glCtx || !program || !u) return;

      const { width, height } = canvas.getBoundingClientRect();
      const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
      const w = Math.max(1, Math.round(width * dpr));
      const h = Math.max(1, Math.round(height * dpr));
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
      glCtx.viewport(0, 0, w, h);

      glCtx.useProgram(program);
      const tSecs = reduceMotion ? 0 : (nowMs - startMs) / 1000;
      glCtx.uniform1f(u.time, tSecs);
      glCtx.uniform2f(u.resolution, w, h);
      glCtx.uniform3f(u.sage, SAGE[0], SAGE[1], SAGE[2]);
      glCtx.uniform3f(u.dust, DUST[0], DUST[1], DUST[2]);
      glCtx.uniform3f(u.bg0, BG0[0], BG0[1], BG0[2]);
      glCtx.drawArrays(glCtx.TRIANGLES, 0, 3);
    };

    const loop = (nowMs: number) => {
      draw(nowMs);
      if (reduceMotion) {
        rafRef.current = 0;
        return;
      }
      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
      mql?.removeEventListener?.("change", onChange);
      // Best-effort cleanup.
      try {
        const g = glRef.current;
        if (g) {
          g.deleteProgram(progRef.current);
          g.deleteShader(vs);
          g.deleteShader(fs);
          if (vao) g.deleteVertexArray(vao);
        }
      } catch {
        /* ignore cleanup errors */
      }
      glRef.current = null;
      progRef.current = null;
      uniformsRef.current = null;
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full block pointer-events-none"
      aria-hidden="true"
      data-testid="terrain-layer-canvas"
    />
  );
}
