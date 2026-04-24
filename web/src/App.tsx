/**
 * App — main dashboard layout (Phase 10 10/10 treatment).
 *
 * Three-row layout:
 * - Top band (64px): StatBand with status chips
 * - Center (flex-1): RanchMap (left ~60%) + Agent Mesh + tabbed right rail
 * - Bottom band (44px): ScenarioStrip
 *
 * Right rail uses a single-expanded tabbed accordion so Memory / Attestation /
 * VetIntake / CrossRanch never fight for vertical space.  CostTicker stays
 * pinned below the Agent Mesh because it is the live-ops heartbeat.
 *
 * Keyboard: ? opens shortcut help, arrow keys cycle right-rail tabs.
 */

import { useState, useMemo, useEffect, useCallback } from "react";
import { StatBand } from "@/components/shared/StatBand";
import { ScenarioStrip } from "@/components/shared/ScenarioStrip";
import { RanchMap } from "@/components/RanchMap";
import { AgentLanes } from "@/components/AgentLanes";
import { CostTicker } from "@/components/CostTicker";
import { AttestationPanel } from "@/components/AttestationPanel";
import { MemoryPanel } from "@/components/MemoryPanel";
import { CrossRanchPanel } from "@/components/CrossRanchPanel";
import { VetIntakePanel } from "@/components/VetIntakePanel";
import { LaptopDroneControl } from "@/components/LaptopDroneControl";
import {
  RightRailAccordion,
  type AccordionTab,
} from "@/components/shared/RightRailAccordion";
import { KeyboardHelp } from "@/components/shared/KeyboardHelp";
import { getSSE } from "@/lib/sse";

export default function App() {
  // Track lightweight counts for tab badges.  Each panel owns its state
  // internally; these counters are derived from SSE so the tab row can
  // surface a "new activity" hint without duplicating panel logic.
  const [memoryCount, setMemoryCount] = useState(0);
  const [attestCount, setAttestCount] = useState(0);
  const [vetCount, setVetCount] = useState(0);
  const [neighborCount, setNeighborCount] = useState(0);

  const handleMemoryWritten = useCallback(() => {
    setMemoryCount((c) => c + 1);
  }, []);
  const handleAttestAppend = useCallback(() => {
    setAttestCount((c) => c + 1);
  }, []);
  const handleVetDraft = useCallback(() => {
    setVetCount((c) => c + 1);
  }, []);
  const handleNeighbor = useCallback(() => {
    setNeighborCount((c) => c + 1);
  }, []);

  useEffect(() => {
    const sse = getSSE();
    sse.on("memory.written", handleMemoryWritten);
    sse.on("attest.append", handleAttestAppend);
    sse.on("vet_intake.drafted", handleVetDraft);
    sse.on("neighbor.handoff", handleNeighbor);
    sse.on("neighbor.alert", handleNeighbor);
    return () => {
      sse.off("memory.written", handleMemoryWritten);
      sse.off("attest.append", handleAttestAppend);
      sse.off("vet_intake.drafted", handleVetDraft);
      sse.off("neighbor.handoff", handleNeighbor);
      sse.off("neighbor.alert", handleNeighbor);
    };
  }, [handleMemoryWritten, handleAttestAppend, handleVetDraft, handleNeighbor]);

  // Clear the tab badge count when user switches to that tab — it's a
  // "new since last view" hint, not a total.
  const handleTabChange = useCallback((id: string) => {
    if (id === "memory") setMemoryCount(0);
    else if (id === "attestation") setAttestCount(0);
    else if (id === "vet") setVetCount(0);
    else if (id === "cross-ranch") setNeighborCount(0);
  }, []);

  const tabs: AccordionTab[] = useMemo(
    () => [
      {
        id: "memory",
        label: "Memory",
        badge: memoryCount || undefined,
        badgeVariant: "sage",
        render: () => <MemoryPanel />,
      },
      {
        id: "attestation",
        label: "Attestation",
        badge: attestCount || undefined,
        badgeVariant: "sky",
        render: () => <AttestationPanel />,
      },
      {
        id: "vet",
        label: "Vet Intake",
        badge: vetCount || undefined,
        badgeVariant: "dust",
        render: () => <VetIntakePanel />,
      },
      {
        id: "cross-ranch",
        label: "Cross-Ranch",
        badge: neighborCount || undefined,
        badgeVariant: "thermal",
        render: () => <CrossRanchPanel />,
      },
      {
        id: "laptop-drone",
        label: "Laptop Drone",
        badge: undefined,
        badgeVariant: "dust",
        render: () => <LaptopDroneControl />,
      },
    ],
    [memoryCount, attestCount, vetCount, neighborCount],
  );

  return (
    <div
      className="flex flex-col h-full overflow-hidden"
      style={{ backgroundColor: "var(--color-bg-0)" }}
    >
      {/* ── Top band ── */}
      <StatBand />

      {/* ── Center: map + right column ── */}
      <div className="flex flex-1 min-h-0 overflow-hidden gap-2 p-2">
        {/* Left ~58%: Ranch Map */}
        <section
          className="flex-[58] min-w-0 overflow-hidden rounded border"
          style={{ borderColor: "var(--color-line)" }}
          aria-label="Ranch map"
        >
          <RanchMap />
        </section>

        {/* Middle ~22%: Agent Mesh + CostTicker stack */}
        <aside
          className="flex-[22] min-w-0 flex flex-col gap-2 overflow-hidden"
          aria-label="Agent mesh"
        >
          <div className="flex-1 min-h-0 overflow-hidden">
            <AgentLanes />
          </div>
          <CostTicker />
        </aside>

        {/* Right ~20%: tabbed accordion (Memory / Attestation / Vet / X-Ranch) */}
        <aside
          className="flex-[20] min-w-0 overflow-hidden"
          aria-label="Supporting panels"
        >
          <RightRailAccordion
            tabs={tabs}
            initialTabId="memory"
            onTabChange={handleTabChange}
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

      {/* Floating keyboard-help button / overlay (press "?" anywhere) */}
      <KeyboardHelp />
    </div>
  );
}
