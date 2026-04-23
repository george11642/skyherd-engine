import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

// VITE_DEMO_MODE is picked up automatically from the environment at build time.
// Vercel production sets VITE_DEMO_MODE=replay via project env vars so the
// deployed SPA runs the replay driver instead of connecting to /events.
// Local `make dashboard` leaves VITE_DEMO_MODE unset (live FastAPI SSE).

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/events": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      output: {
        // DASH-06: split the two heaviest canvas components into their own
        // chunks so the initial bundle stays under the Lighthouse >= 90 budget.
        manualChunks: {
          "ranch-map": ["./src/components/RanchMap.tsx"],
          "cross-ranch": ["./src/components/CrossRanchView.tsx"],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/test-setup.ts", "src/sw.ts"],
    },
  },
});
