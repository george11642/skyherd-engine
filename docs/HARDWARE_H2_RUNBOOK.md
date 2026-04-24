# Hardware H2 Runbook — Desk Coyote → SITL Drone Takeoff

**Phase 6 deliverable.**  One-command laptop demo of the full SkyHerd event
chain: cardboard coyote (thermal sensor emulator) → MQTT broker →
pi-to-mission bridge → FenceLineDispatcher → ArduPilot SITL drone takeoff
+ patrol → acoustic deterrent emit → attestation.  Zero physical hardware
required.

## 1. Summary

A desk coyote fires a thermal-hit event every 2 seconds.  The
`pi_to_mission` bridge picks it up, classifies it via the
FenceLineDispatcher simulation handler, and commands a SITL drone to take
off and patrol to the breach waypoint.  The speaker bridge subscribes to
the deterrent topic and plays a 12 kHz predator-frequency WAV (muted in
containers; unmutes on a real laptop).  The dashboard shows the cascade in
real time.

**Expected time to "oh damn" moment: under 60 seconds.**

## 2. Prerequisites

- Docker Engine ≥ 20.10 + Docker Compose v2
- ~2 GB of free disk space (SITL image is ~1.3 GB)
- Ports 1883 (MQTT), 5760 (SITL TCP), 8000 (dashboard), 14540 (MAVLink UDP)
- **No Raspberry Pi required.**  The coyote harness runs as a container.

## 3. One-shot boot

From the repo root:

```bash
make hardware-demo-sim
open http://localhost:8000
```

Total first-run build time ≈ 3-4 min (SITL image pull + local Dockerfile
build).  Subsequent runs ≈ 20 s (layer cache hits).

Follow the live log stream:

```bash
docker compose -f docker-compose.hardware-demo.yml logs -f
```

## 4. What you should see

- **Dashboard panels** at `http://localhost:8000`:
  - Live thermal reading stream from the coyote harness.
  - FenceLineDispatcher wake-event pulse every 2 s.
  - Drone state transitions: `STABILIZE` → `GUIDED` (armed/takeoff) → `AUTO`
    (patrol) → (steady-state hover at the breach waypoint).
  - Attestation ledger ticker — seq numbers monotonically increasing.
- **Logs**:
  - `skyherd-edge-coyote` — a new `predator.thermal_hit` every 2 s.
  - `skyherd-pi-to-mission` — `wake_event` / `mission.launched`
    / `deterrent.played` per event.
  - `skyherd-speaker` — `SpeakerBridge: deterrent NOP` (mute mode).
  - `skyherd-sitl` — MAVLink arming / waypoint-upload output.
  - `skyherd-live` — SSE event emission to dashboard.

## 5. Shutdown

```bash
make hardware-demo-sim-down
```

Cleans up all six containers.  SITL image stays cached for next run.

## 6. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `docker compose up` hangs on SITL pull | Use the prebuilt local image: `SITL_IMAGE=skyherd-sitl:local make sitl-up && make hardware-demo-sim` |
| Port 14540 already in use | `SITL_PORT_UDP=14541 make hardware-demo-sim` |
| Dashboard returns 502 | `docker compose -f docker-compose.hardware-demo.yml logs skyherd-live` — check the uvicorn startup output |
| Coyote harness silent | `docker compose logs skyherd-edge-coyote` — verify `COYOTE_INTERVAL_S=2.0` is set |
| Deterrent "fires but silent" | Expected in container (`SKYHERD_DETERRENT=mute`).  Unset on a laptop with audio: `SKYHERD_DETERRENT=play uv run skyherd-edge deterrent` |
| SITL arms but never takes off | Check `skyherd-pi-to-mission` logs for `mission.failed` — often a MAVLink timeout.  `docker compose restart sitl` and re-trigger. |

## 7. Architecture

```
 ┌───────────────────┐    skyherd/ranch_a/thermal/coyote_cam
 │  skyherd-edge-    │───────────────────────┐
 │      coyote       │    skyherd/ranch_a/alert/thermal_hit
 │ (CoyoteHarness)   │───────────────────────┤
 └───────────────────┘                       │
                                             ▼
                                 ┌────────────────────┐
                                 │ skyherd-mosquitto  │
                                 │    (MQTT broker)   │
                                 └────────┬───────────┘
                                          │
         ┌────────────────────────────────┼────────────────────────────┐
         │                                │                            │
         ▼                                ▼                            ▼
┌────────────────────┐   ┌────────────────────────────┐    ┌────────────────────┐
│ skyherd-pi-to-     │   │ skyherd-live (FastAPI+SSE) │    │ skyherd-speaker    │
│    mission         │   │   dashboard @ :8000        │    │ (SpeakerBridge)    │
│ (PiToMissionBridge)│   └────────────────────────────┘    │ skyherd/ranch_a/   │
└──────────┬─────────┘                                     │   deterrent/play   │
           │                                               └────────────────────┘
           │ launch_drone(mission=fence_patrol,target_lat,lon,alt_m)
           ▼
┌────────────────────┐
│    skyherd-sitl    │
│ ArduPilot Copter   │
│   MAVLink @ :14540 │
└────────────────────┘
```

## 8. Determinism guarantee

`SKYHERD_SEED=42` flows to the coyote harness + pi-to-mission mission-id
generator; the ledger entries are byte-identical across replays (after
timestamp sanitization).  Run `make demo SEED=42 SCENARIO=all` on the host
to verify the in-process determinism gate is still GREEN alongside the
hardware demo.

## 9. Next up — Phase 7 (H3, Mavic Air 2 SDK hardening)

When George's Mavic arrives Friday 4/24, Phase 7 swaps `DRONE_BACKEND=sitl`
for `DRONE_BACKEND=mavic` and pipes the exact same MQTT chain into the
real drone.  No code changes required — just set the env var and rebuild.
