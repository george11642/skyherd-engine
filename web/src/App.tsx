/**
 * App — main dashboard layout.
 *
 * Split layout:
 * - Left 60%: RanchMap (Canvas)
 * - Right 40%: AgentLanes (top) + CostTicker (strip) + AttestationPanel (bottom)
 */

import { useState } from "react";
import { RanchMap } from "@/components/RanchMap";
import { AgentLanes } from "@/components/AgentLanes";
import { CostTicker } from "@/components/CostTicker";
import { AttestationPanel } from "@/components/AttestationPanel";

export default function App() {
  const [attestCollapsed, setAttestCollapsed] = useState(false);

  return (
    <div className="flex flex-col h-full bg-slate-950 overflow-hidden">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold tracking-tight text-slate-100">
            Sky<span className="text-green-400">Herd</span>
          </span>
          <span className="text-xs text-slate-500 font-mono">ranch_a · sim</span>
        </div>
        <nav className="flex gap-3 text-xs">
          <a
            href="/"
            className="text-green-400 font-semibold"
            aria-current="page"
          >
            Dashboard
          </a>
          <a
            href="/rancher"
            className="text-slate-500 hover:text-slate-300 transition-colors"
          >
            Rancher PWA
          </a>
        </nav>
      </header>

      {/* Main content area */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left: Ranch Map */}
        <section
          className="flex-[3] min-w-0 p-3 overflow-hidden"
          aria-label="Ranch map"
        >
          <div className="h-full rounded-xl border border-slate-700/60 overflow-hidden bg-slate-900">
            <RanchMap />
          </div>
        </section>

        {/* Right: Agents + Cost + Attestation */}
        <aside className="flex-[2] min-w-0 flex flex-col gap-3 p-3 overflow-hidden">
          {/* Agent Lanes — takes available space */}
          <div className="flex-1 min-h-0 overflow-hidden">
            <AgentLanes />
          </div>

          {/* Cost Ticker — fixed strip */}
          <CostTicker />

          {/* Attestation Panel — collapsible bottom sheet */}
          <AttestationPanel
            collapsed={attestCollapsed}
            onToggle={() => setAttestCollapsed((v) => !v)}
          />
        </aside>
      </div>
    </div>
  );
}
