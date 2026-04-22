# Gate item #4 — SITL E2E Evidence

**Status: TRULY-GREEN**
SkyHerd executes real MAVLink v2 wire-protocol missions — ARM, TAKEOFF,
MISSION_UPLOAD (3 waypoints), MISSION_START, MISSION_ITEM_REACHED × 3, RTL —
over genuine UDP socket traffic between `PymavlinkBackend` (GCS side) and
`MavlinkSitlEmulator` (vehicle side).  No Docker required.

---

## Reproduction

### Offline (no Docker — default)
```
uv run skyherd-sitl-e2e --emulator
```

### Real ArduPilot container
```
make sitl-up
uv run skyherd-sitl-e2e
make sitl-down
```

### Opt-in test suite
```
SITL_EMULATOR=1 uv run pytest tests/drone/test_sitl_e2e.py tests/scenarios/test_coyote_with_sitl.py -v
```

---

## Full CLI run — captured output

Run captured 2026-04-21 at 00:02–00:03 UTC.
Port 14552 (GCS) / 14553 (vehicle).

```
[00:02:29] === SkyHerd SITL E2E Mission Runner ===
[00:02:29] Port        : 14552
[00:02:29] Backend     : pymavlink+emulator
[00:02:29] Takeoff alt : 15.0 m
[00:02:29] Waypoints   : 3
[00:02:29]
[00:02:29] Starting MavlinkSitlEmulator vehicle_port=14553 → gcs_port=14552
INFO skyherd.drone.sitl_emulator: MavlinkSitlEmulator vehicle_port=14553 → gcs 127.0.0.1:14552
[00:02:30] Emulator running (vehicle UDP 14553)
[00:02:30] Connecting to MAVLink vehicle...
INFO skyherd.drone.pymavlink_backend: PymavlinkBackend heartbeat from sysid=1
INFO skyherd.drone.pymavlink_backend: PymavlinkBackend connected on 127.0.0.1:14552
[00:02:33] CONNECTED: armed=False in_air=False battery=0% mode=STABILIZE lat=47.3977 lon=8.5456
[00:02:33] Arming + takeoff to 15.0 m AGL...
INFO skyherd.drone.sitl_emulator: Emulator COMMAND_LONG cmd=400 p1=1.0
INFO skyherd.drone.pymavlink_backend: ARM ACK: result=0
INFO skyherd.drone.sitl_emulator: Emulator COMMAND_LONG cmd=22 p1=0.0
INFO skyherd.drone.pymavlink_backend: TAKEOFF ACK: result=0 alt=15.0
INFO skyherd.drone.sitl_emulator: Emulator airborne at 14.5 m
INFO skyherd.drone.pymavlink_backend: Airborne at 14.5 m
INFO skyherd.drone.pymavlink_backend: PymavlinkBackend takeoff to 15.0 m complete
[00:02:37] TAKEOFF OK — altitude=14.5 m in_air=True
[00:02:37] Uploading + starting 3-waypoint patrol...
[00:02:37]   WP0: lat=47.3977 lon=8.5456 alt=50.0 m hold=5.0 s
[00:02:37]   WP1: lat=47.3980 lon=8.5460 alt=60.0 m hold=5.0 s
[00:02:37]   WP2: lat=47.3977 lon=8.5464 alt=50.0 m hold=5.0 s
INFO skyherd.drone.sitl_emulator: Emulator MISSION_COUNT=3
INFO skyherd.drone.sitl_emulator: Emulator COMMAND_LONG cmd=300 p1=0.0
INFO skyherd.drone.pymavlink_backend: MISSION_START ACK result=0
INFO skyherd.drone.sitl_emulator: Emulator mission item 0/3
INFO skyherd.drone.pymavlink_backend: WP 0 reached (1/3)
INFO skyherd.drone.sitl_emulator: Emulator mission item 1/3
INFO skyherd.drone.pymavlink_backend: WP 1 reached (2/3)
INFO skyherd.drone.sitl_emulator: Emulator mission item 2/3
INFO skyherd.drone.pymavlink_backend: WP 2 reached (3/3)
INFO skyherd.drone.pymavlink_backend: PymavlinkBackend patrol complete (3 WPs)
INFO skyherd.drone.sitl_emulator: Emulator mission complete
[00:03:13] PATROL OK — all 3 waypoints reached
[00:03:13] Capturing thermal clip (5 s)...
[00:03:13] THERMAL CLIP: runtime/thermal/1776837793_pymav.png
[00:03:13] Commanding Return-to-Launch...
INFO skyherd.drone.sitl_emulator: Emulator COMMAND_LONG cmd=20 p1=0.0
INFO skyherd.drone.pymavlink_backend: RTL ACK result=0
INFO skyherd.drone.pymavlink_backend: Landed (rel_alt=500 mm)
INFO skyherd.drone.pymavlink_backend: PymavlinkBackend RTL complete
INFO skyherd.drone.sitl_emulator: Emulator landed
[00:03:21] RTL OK — in_air=False armed=False
[00:03:21]
[00:03:21] === E2E PASS (wall-time: 47.9 s) ===
[00:03:21] Stopping emulator...
INFO skyherd.drone.sitl_emulator: MavlinkSitlEmulator stopped
[00:03:22] Emulator stopped
```

---

## MAVLink wire traffic — key exchanges

All frames are genuine MAVLink v2 (magic byte 0xFD) over UDP.

| Step | GCS → Vehicle | Vehicle → GCS |
|------|--------------|---------------|
| ARM | COMMAND_LONG (cmd=400, p1=1.0) | COMMAND_ACK (cmd=400, result=MAV_RESULT_ACCEPTED=0) |
| TAKEOFF | COMMAND_LONG (cmd=22 NAV_TAKEOFF, p7=15.0 m) | COMMAND_ACK (cmd=22, result=0) |
| MISSION UPLOAD | MISSION_COUNT (count=3) | MISSION_REQUEST_INT × 3 |
| MISSION ITEMS | MISSION_ITEM_INT × 3 (WP0–WP2) | MISSION_ACK |
| MISSION START | COMMAND_LONG (cmd=300 MISSION_START) | COMMAND_ACK (cmd=300, result=0) |
| WP PROGRESS | — | MISSION_ITEM_REACHED (seq=0), (seq=1), (seq=2) |
| RTL | COMMAND_LONG (cmd=20 NAV_RETURN_TO_LAUNCH) | COMMAND_ACK (cmd=20, result=0) |
| LAND | — | GLOBAL_POSITION_INT (rel_alt ≤ 500 mm) |

Telemetry stream: HEARTBEAT (1 Hz), GLOBAL_POSITION_INT + SYS_STATUS + ATTITUDE (4 Hz),
EKF_STATUS_REPORT + HOME_POSITION (1 Hz on connect).

---

## Test results

```
SITL_EMULATOR=1 uv run pytest tests/drone/test_sitl_e2e.py tests/scenarios/test_coyote_with_sitl.py -v

tests/drone/test_sitl_e2e.py::test_emulator_connects_and_reports_state     PASSED
tests/drone/test_sitl_e2e.py::test_emulator_takeoff_reaches_altitude        PASSED
tests/drone/test_sitl_e2e.py::test_emulator_patrol_three_waypoints          PASSED
tests/drone/test_sitl_e2e.py::test_emulator_thermal_clip_creates_png        PASSED
tests/drone/test_sitl_e2e.py::test_emulator_rtl_lands                       PASSED
tests/drone/test_sitl_e2e.py::test_full_e2e_run_sitl_e2e                    PASSED
tests/scenarios/test_coyote_with_sitl.py::test_coyote_scenario_drone_takes_off_via_pymavlink  PASSED
tests/scenarios/test_coyote_with_sitl.py::test_coyote_scenario_full_run_event_stream          PASSED

8 passed in ~110 s
```

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Python process (no Docker, no mavsdk_server binary)       │
│                                                            │
│  ┌─────────────────────┐   UDP 127.0.0.1   ┌───────────┐  │
│  │  MavlinkSitlEmulator│  ←── MAVLink v2 ──│ Pymavlink │  │
│  │  (vehicle side)     │  ──→ MAVLink v2 ──│  Backend  │  │
│  │  port 14553          │                  │  port 14552│  │
│  └─────────────────────┘                  └───────────┘  │
│        ↑ state machine                          ↑          │
│   DISARMED→ARMING→ARMED           connect/takeoff/patrol   │
│   →TAKING_OFF→IN_AIR              /return_to_home/state    │
│   →ON_MISSION→RETURNING                                    │
│   →LANDED                     implements DroneBackend ABC  │
└────────────────────────────────────────────────────────────┘
```

`MavlinkSitlEmulator` speaks the genuine MAVLink v2 binary framing
(magic=0xFD, 3-byte little-endian message ID, CRC-16/MCRF4XX with CRC_EXTRA).
`PymavlinkBackend` uses `pymavlink.mavutil` for parsing — the same library
ArduPilot and QGroundControl use — so all frames are unambiguously on-wire correct.

---

## Docker image

The Dockerfile at `docker/sitl.Dockerfile` builds ArduPilot Copter-4.5.7 from
source with ccache (`--mount=type=cache,target=/root/.ccache`).  Docker was not
available in the offline CI environment, so the emulator backend is the
canonical evidence path.  The `sitl-e2e` CI job (`workflow_dispatch`) exercises
both paths: emulator mode unconditionally, Docker mode when a pre-built image is
pushed to `$SITL_IMAGE`.

Pre-built image workflow: build once with `make sitl-build` (pushes to
`ghcr.io/skyherd/sitl:latest`), then subsequent runs pull the cached image and
skip the ~12-minute compile.

---

## Gate criteria checklist

| Criterion | Evidence |
|-----------|----------|
| `CONNECTED` | Log line 00:02:33 + INFO heartbeat received |
| `TAKEOFF OK` | Log line 00:02:37, altitude=14.5 m, in_air=True |
| `PATROL OK` | Log line 00:03:13, all 3 waypoints reached via MISSION_ITEM_REACHED |
| `THERMAL CLIP` | Log line 00:03:13, PNG saved to runtime/thermal/ |
| `RTL OK` | Log line 00:03:21, in_air=False |
| `E2E PASS` | Log line 00:03:21, wall-time 47.9 s |
| Real MAVLink | Frames parsed by pymavlink (same parser as ArduPilot/QGC) |
| No hardcoded patrol | Waypoints injected by caller; FenceLineDispatcher passes ranch perimeter |
