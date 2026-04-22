# Cross-Ranch Mesh

## What it demonstrates

Two simulated ranches — Mesa Verde Ranch (ranch_a) and Mesa del Sol Ranch (ranch_b) — share an eastern/western boundary fence. Each ranch runs its own independent 5-agent mesh. When ranch_a's FenceLineDispatcher confirms a coyote at the shared fence, a `NeighborBroadcaster` immediately publishes a compact `predator_confirmed` event to the inter-ranch topic `skyherd/neighbor/ranch_a/ranch_b/predator_confirmed`. Ranch_b's `NeighborListener` intercepts the event, deduplicates it, and wakes ranch_b's FenceLineDispatcher with a synthetic `neighbor_alert` wake event. Ranch_b's agent responds in `pre_position` mode: it dispatches a drone to the shared fence and logs a `neighbor_handoff` dashboard entry — without paging Wes or creating a duplicate alert. The result is agent-to-agent choreography with zero human involvement and zero duplicate notifications.

What makes this the clearest Managed Agents demo: two independent Claude sessions coordinate through a shared MQTT protocol, each making autonomous decisions in their own context window. Ranch_b acts on a leading indicator before the coyote ever crosses into its territory. The shared fence is attested twice — once per ranch ledger — giving an insurance-grade audit trail spanning both properties.

## Running the demo

**CLI (recommended for judges):**

```bash
skyherd-demo play cross_ranch_coyote
# or
uv run python -c "from skyherd.scenarios.cross_ranch_coyote import run_cross_ranch; r = run_cross_ranch(); print(r['outcome_passed'])"
```

**Dashboard side-by-side view:**

```
http://localhost:8000/?view=cross-ranch
```

Both ranch canvases appear side by side. When the neighbor handoff fires, the shared fence boundary pulses amber, ranch_a's label reads `ACTIVE`, ranch_b's label reads `PRE-POSITIONING`, and the `HandoffBanner` strip shows the full event payload including `rancher_paged: no (silent handoff)`.

## The 15-second judge explanation

Ranch A detects a coyote at the shared fence. Its FenceLineDispatcher — a Managed Agent sleeping at $0 — wakes, confirms the threat, and broadcasts a signed neighbor alert over MQTT. Ranch B's FenceLineDispatcher wakes from its own idle session, reads the alert, and pre-positions a patrol drone before the coyote arrives — no human in the loop, no duplicate phone call. Two Claude sessions, one protocol, zero rancher interruption. That is the operating system for remote land assets.

## Architecture

```
ranch_a mesh                          ranch_b mesh
─────────────────────────────────     ─────────────────────────────────
FenceLineDispatcher (Session A)        FenceLineDispatcher (Session B)
    │ confirms coyote at fence_east         ▲ wakes on neighbor_alert
    │                                       │
    ▼                                       │
NeighborBroadcaster                  NeighborListener
    │ publishes predator_confirmed          │ dedupes + routes
    └──────── skyherd/neighbor/ranch_a/ranch_b/predator_confirmed ──────►
                        (in-process asyncio.Queue in sim;
                         real MQTT topic in production)
```

## Key files

| File | Role |
|---|---|
| `src/skyherd/agents/mesh_neighbor.py` | NeighborBroadcaster, NeighborListener, CrossRanchMesh |
| `src/skyherd/scenarios/cross_ranch_coyote.py` | End-to-end scenario + assert_outcome |
| `src/skyherd/agents/fenceline_dispatcher.py` | neighbor_alert routing (append-only additions) |
| `src/skyherd/world/terrain.py` | NeighborRef + TerrainConfig.neighbors field |
| `worlds/ranch_b.yaml` | Mesa del Sol Ranch world definition |
| `web/src/components/CrossRanchView.tsx` | Dashboard two-up view |
| `src/skyherd/server/events.py` | broadcast_neighbor_handoff SSE method |
| `tests/agents/test_neighbor_mesh.py` | Unit tests (broadcaster, listener, mesh) |
| `tests/scenarios/test_cross_ranch_coyote.py` | Scenario integration tests |
