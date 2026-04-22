/**
 * App — main dashboard layout.
 *
 * Three-row layout:
 * - Top band (64px): StatBand with status chips
 * - Center (flex-1): RanchMap (left 60%) + Agent Mesh / Cost / Attestation (right 40%)
 * - Bottom band (120px): Cost Ticker strip + Scenario Strip + Attestation summary
 */

import { useState } from "react";
import { StatBand } from "@/components/shared/StatBand";
import { ScenarioStrip } from "@/components/shared/ScenarioStrip";
import { RanchMap } from "@/components/RanchMap";
import { AgentLanes } from "@/components/AgentLanes";
import { CostTicker } from "@/components/CostTicker";
import { AttestationPanel } from "@/components/AttestationPanel";

export default function App() {
  const [attestCollapsed, setAttestCollapsed] = useState(false);

  return (
    <div
      className="flex flex-col h-full overflow-hidden"
      style={{ backgroundColor: "var(--color-bg-0)" }}
    >
      {/* ── Top band ── */}
      <StatBand />

      {/* ── Center: map + right panel ── */}
      <div className="flex flex-1 min-h-0 overflow-hidden gap-2 p-2">
        {/* Left 60%: Ranch Map */}
        <section
          className="flex-[3] min-w-0 overflow-hidden rounded border"
          style={{ borderColor: "var(--color-line)" }}
          aria-label="Ranch map"
        >
          <RanchMap />
        </section>

        {/* Right 40%: Agent Mesh + Cost + Attestation */}
        <aside
          className="flex-[2] min-w-0 flex flex-col gap-2 overflow-hidden"
          aria-label="Monitoring panels"
        >
          {/* Agent Mesh — fills available space */}
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

      {/* ── Bottom band ── */}
      <div
        className="shrink-0 flex items-center gap-4 px-3 py-2 border-t"
        style={{
          height: "44px",
          backgroundColor: "var(--color-bg-1)",
          borderColor: "var(--color-line)",
        }}
      >
        <ScenarioStrip />
      </div>
    </div>
  );
}
