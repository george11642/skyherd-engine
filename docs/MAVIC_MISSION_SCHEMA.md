# MAVIC_MISSION_SCHEMA.md

**Schema version:** 1 (frozen 2026-04-24)
**Canonical model:** `src/skyherd/drone/mission_schema.py` (`MissionV1`)
**Consumers:** iOS `SkyHerdCompanion` (`Sources/.../CommandRouter.swift`),
Android `SkyHerdCompanion` (`.../kotlin/com/skyherd/companion/DroneControl.kt`),
`src/skyherd/drone/mavic_adapter.py` (`patrol_mission`).

---

## 1. Overview

The SkyHerd agent mesh produces mission packets that flow through three
hops before reaching the aircraft:

```
 FenceLineDispatcher / CalvingWatch / (future) CrossRanchCoordinator
        │  emits  MissionV1 (Python Pydantic model)
        ▼
 MavicAdapter.patrol_mission(MissionV1)
        │  serialises to JSON wire format
        ▼
 Active leg (DJI via companion app  |  MAVSDK over USB-C OTG)
        │  parses JSON; dispatches to DJI SDK V5 / MAVLink
        ▼
 Drone
```

The schema is versioned so that a mobile-app update can lag the
Python-side by some weeks without breaking the chain. Adding fields is
non-breaking (the schema's `extra="allow"` policy lets older parsers
ignore unknown fields); removing or renaming fields IS breaking and
requires a `version` bump.

---

## 2. Schema v1 reference

All field types follow Pydantic v2 conventions; wire format is plain
JSON (no exotic encodings).

### Top-level `MissionV1`

| Field                    | Type                           | Required | Bounds                    | Notes |
|--------------------------|--------------------------------|----------|---------------------------|-------|
| `version`                | `Literal[1]`                   | yes      | must be `1`               | Bumping is breaking |
| `metadata`               | `MissionMetadata`              | yes      | —                         | See below |
| `waypoints`              | `list[Waypoint]`               | yes      | 1 ≤ len ≤ 64              | See Waypoint section |
| `deterrent_tone_hz`      | `int \| null`                  | no       | 500 ≤ v ≤ 20000           | Optional deterrent |
| `deterrent_duration_s`   | `float \| null`                | no       | 0.0 ≤ v ≤ 60.0            | Optional deterrent |
| `failover`               | `FailoverHint`                 | no       | default = auto            | See FailoverHint |
| `<extra>`                | any                            | no       | —                         | Forward compat; ignored by v1 readers |

### `MissionMetadata`

| Field                 | Type            | Required | Bounds            | Notes |
|-----------------------|-----------------|----------|-------------------|-------|
| `mission_id`          | `str`           | yes      | 1 ≤ len ≤ 64      | Opaque id; see `MavicAdapter._next_mission_id` |
| `ranch_id`            | `str`           | yes      | 1 ≤ len ≤ 64      | Matches ranch YAML name |
| `scenario`            | `str \| null`   | no       | —                 | e.g. `"coyote_fence"`, `"wildfire"` |
| `wind_kt`             | `float \| null` | no       | 0 ≤ v ≤ 100       | Pre-flight wind speed |
| `battery_floor_pct`   | `float`         | no       | 0 ≤ v ≤ 100       | default 30.0 |
| `geofence_version`    | `str \| null`   | no       | —                 | Matches ranch world YAML version |
| `issued_ts`           | `float \| null` | no       | —                 | Epoch seconds; monotonic in replay |
| `issued_by`           | `str \| null`   | no       | —                 | Agent id |

### `Waypoint` (reused from `interface.py`)

| Field    | Type   | Required | Notes |
|----------|--------|----------|-------|
| `lat`    | float  | yes      | Degrees |
| `lon`    | float  | yes      | Degrees |
| `alt_m`  | float  | yes      | Metres AGL |
| `hold_s` | float  | no       | Seconds to hover; default 0.0 |

### `FailoverHint`

| Field                  | Type                                | Default | Notes |
|------------------------|-------------------------------------|---------|-------|
| `preferred_leg`        | `"dji" \| "mavsdk" \| "auto"`       | `auto`  | Forces leg selection |
| `retry_on_other_leg`   | `bool`                              | `true`  | Single-retry behaviour |
| `retry_budget`         | `int` (0 ≤ v ≤ 8)                   | `1`     | Max leg swaps per mission |

---

## 3. Example payloads

### 3.1 Coyote at fence (typical)

```json
{
  "version": 1,
  "metadata": {
    "mission_id": "mission_00000042",
    "ranch_id": "ranch_a",
    "scenario": "coyote_fence",
    "wind_kt": 8.5,
    "battery_floor_pct": 30.0,
    "geofence_version": "ranch_a@v3",
    "issued_ts": 1745884800.0,
    "issued_by": "FenceLineDispatcher"
  },
  "waypoints": [
    {"lat": 34.1234, "lon": -106.5678, "alt_m": 30.0, "hold_s": 8.0},
    {"lat": 34.1236, "lon": -106.5676, "alt_m": 30.0, "hold_s": 0.0}
  ],
  "deterrent_tone_hz": 12000,
  "deterrent_duration_s": 6.0,
  "failover": {
    "preferred_leg": "auto",
    "retry_on_other_leg": true,
    "retry_budget": 1
  }
}
```

### 3.2 Wildfire evacuation (multi-waypoint, no deterrent)

```json
{
  "version": 1,
  "metadata": {
    "mission_id": "mission_00000051",
    "ranch_id": "ranch_a",
    "scenario": "wildfire",
    "wind_kt": 18.0,
    "battery_floor_pct": 40.0,
    "issued_by": "GrazingOptimizer"
  },
  "waypoints": [
    {"lat": 34.10, "lon": -106.50, "alt_m": 50.0, "hold_s": 2.0},
    {"lat": 34.11, "lon": -106.51, "alt_m": 50.0, "hold_s": 2.0},
    {"lat": 34.12, "lon": -106.52, "alt_m": 50.0, "hold_s": 2.0},
    {"lat": 34.13, "lon": -106.53, "alt_m": 50.0, "hold_s": 10.0}
  ],
  "failover": {"preferred_leg": "mavsdk"}
}
```

### 3.3 Calving observation (minimum payload)

```json
{
  "version": 1,
  "metadata": {
    "mission_id": "mission_00000088",
    "ranch_id": "ranch_a",
    "scenario": "calving"
  },
  "waypoints": [
    {"lat": 34.123, "lon": -106.567, "alt_m": 20.0, "hold_s": 30.0}
  ]
}
```

---

## 4. Forward / backward compatibility

| Change                               | Breaking? | Action |
|--------------------------------------|-----------|--------|
| Add optional field to top-level      | no        | Ship in Python; apps ignore until they support it |
| Add optional field to submodel       | no        | Same |
| Add new scenario string              | no        | No code change needed |
| Tighten bounds on existing field     | yes       | Bump `version` |
| Remove field                         | yes       | Bump `version` |
| Rename field                         | yes       | Bump `version` |
| Change field type                    | yes       | Bump `version` |
| Add required field                   | yes       | Bump `version` |

The `extra="allow"` config on `MissionV1` means older companion apps
will silently ignore fields they don't understand. That is intentional:
a Friday-shipped Python update can describe richer missions for later
app updates to pick up, without breaking a demo laptop that's still on
the prior app build.

---

## 5. Companion-app parsing notes + MQTT topic scheme

### Unified MQTT topic scheme (Phase 7.2)

Both iOS and Android share a single topic base.  The trailing platform
segment identifies the sender; there is no routing divergence anymore
(previous builds had `ack/ios` vs `state/ack` mismatch — see Phase 7.2
Audit 2).

| Direction  | Topic                              | Publisher | Payload              | Retained |
|------------|------------------------------------|-----------|----------------------|----------|
| broker → app   | `skyherd/drone/cmd/#`          | MavicAdapter | DroneCommand / MissionV1 | no |
| iOS → broker   | `skyherd/drone/ack/ios`        | iOS app   | DroneAck             | no       |
| iOS → broker   | `skyherd/drone/state/ios`      | iOS app   | MQTTStatePayload     | yes (latest) |
| iOS → broker   | `skyherd/drone/status/ios`     | iOS app   | `online`/`offline`   | yes      |
| Android → broker | `skyherd/drone/ack/android`  | Android app | DroneAck           | no       |
| Android → broker | `skyherd/drone/state/android`| Android app | state JSON         | yes (latest) |
| Android → broker | `skyherd/drone/status/android` | Android app | online/offline   | yes      |

The `/status/{platform}` topic is published with QoS 1 + retained and uses
an MQTT Will to auto-mark the client `offline` on unexpected disconnect —
the laptop's lost-signal watchdog subscribes here so it can dual-confirm a
companion-app outage within one MQTT keep-alive interval.

### Envelope acceptance

Both companion apps accept EITHER shape on the command topic:

```json
// Legacy
{"cmd":"takeoff","args":{"alt_m":5.0},"seq":1}

// MissionV1
{"version":1,"metadata":{...},"command":{"cmd":"takeoff","args":{...}},"seq":1}
```

### iOS (Swift)

`DroneCommand.init(from: Decoder)` detects the envelope shape via the
presence of a `version` key and decodes `metadata` into a typed
`MissionMetadata` struct. `CommandRouter` reads `metadata.battery_floor_pct`
and `metadata.wind_kt` per-call when present.

### Android (Kotlin)

`DroneControl.parseEnvelope(payload)` performs the same detection and
returns `Parsed(cmd, args, seq, metadata)`.  `applyMissionMetadata(...)`
copies `battery_floor_pct` onto the `SafetyGuards` instance before each
command.

### Python (adapter side)

Import `MissionV1` and call `.to_wire()` before MQTT send; parse with
`MissionV1.from_wire(payload)` when consuming.

### Lost-signal watchdog contract

When the companion-to-broker MQTT link drops for ≥ 30 s **while the drone
is in-air**, both apps fire their local RTH:

- iOS: `LostSignalWatchdog.tick` (see
  `ios/SkyHerdCompanion/Sources/SkyHerdCompanion/LostSignalWatchdog.swift`)
- Android: `DroneControl.startLostSignalWatchdog`

The threshold is 30 s on both platforms (parity, Phase 7.2).  Both can be
disabled at runtime via `autoRthEnabled` / `autoRthOnLostSignal`.

---

## 6. Version bump protocol

When a schema change is necessary:

1. **Branch** — create `schema-v2` feature branch.
2. **Add `MissionV2`** alongside `MissionV1` — do NOT mutate v1.
3. **Bump `SCHEMA_VERSION`** constant to the new version value.
4. **Update both companion apps** to accept BOTH v1 and v2 (dispatch
   on the `version` field).
5. **Update `MavicAdapter.patrol_mission`** to emit v2 by default with
   an env-var override (`SKYHERD_MISSION_SCHEMA=v1`) for rollback.
6. **Soak for 1 week** on SITL before retiring v1.
7. **After 1 week**, remove v1 emit code. v1 parse code stays for at
   least one additional release.

---

## 7. See also

- `src/skyherd/drone/mission_schema.py` — canonical Pydantic model.
- `src/skyherd/drone/mavic_adapter.py` — consumer side.
- `docs/HARDWARE_MAVIC_PROTOCOL.md` — lower-level MQTT/WebSocket
  envelope (unchanged by this schema; missions ride inside the existing
  `cmd: "patrol"` envelope's `args`).
- `docs/HARDWARE_H3_RUNBOOK.md` — operational guide.

---

_Frozen 2026-04-24. Next review after Phase 9 (demo video) to confirm
payload shape on camera._
