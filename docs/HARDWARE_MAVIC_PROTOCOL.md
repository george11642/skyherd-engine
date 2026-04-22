# HARDWARE_MAVIC_PROTOCOL — Canonical SkyHerd Mavic Wire Protocol

This document defines the **single source of truth** for the JSON messages
exchanged between the SkyHerd Engine Python backend and the iOS / Android
SkyHerdCompanion apps.  All three implementations (Python `mavic.py`, Swift
`CommandRouter.swift`, Kotlin `CommandRouter.kt`) must conform to this spec.

---

## Transport

- **Primary**: WebSocket (RFC 6455), bidirectional.  The **companion app** opens a
  WebSocket **server** on port 8765; the **Python backend** connects as a client.
- **Secondary (telemetry bus)**: MQTT v3.1.1 on the ranch Mosquitto broker.  The
  companion app publishes state and ACKs; the backend subscribes.  This transport
  is used for passive telemetry and does not carry commands in normal operation.

---

## Message Directions

```
Python backend ──cmd──► companion app   (WebSocket, topic skyherd/drone/cmd/*)
companion app  ──ack──► Python backend  (WebSocket + MQTT skyherd/drone/ack/ios)
companion app ──state─► broker          (MQTT skyherd/drone/state/ios)
```

---

## Command Envelope (Python → App)

```json
{
  "cmd":  "<string>",
  "args": { "<key>": "<value>", … },
  "seq":  <integer>
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `cmd` | string | yes | Command name (see Commands below) |
| `args` | object | yes | Command-specific arguments (may be `{}`) |
| `seq` | integer | yes | Monotonically increasing sequence counter per session.  Used for de-duplication and ACK matching. |

---

## ACK Envelope (App → Python)

Success:
```json
{
  "ack":    "<string>",
  "result": "ok",
  "seq":    <integer>
}
```

Success with data (e.g. `get_state`):
```json
{
  "ack":    "get_state",
  "result": "ok",
  "seq":    2,
  "data":   { "armed": false, "in_air": false, "altitude_m": 0.0,
              "battery_pct": 85.0, "mode": "STANDBY", "lat": 36.1, "lon": -105.2 }
}
```

Error:
```json
{
  "ack":     "<string>",
  "result":  "error",
  "message": "<error-code>",
  "seq":     <integer>
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `ack` | string | yes | Mirrors the `cmd` field of the command being acknowledged |
| `result` | `"ok"` or `"error"` | yes | Outcome |
| `seq` | integer | yes | Mirrors the `seq` of the incoming command |
| `message` | string | error only | One of the error codes below |
| `data` | object | sometimes | Populated for `get_state`; `null` otherwise |

---

## Commands

### `takeoff`

```json
{"cmd": "takeoff", "args": {"alt_m": 5.0}, "seq": 1}
```

| Arg | Type | Default | Description |
|---|---|---|---|
| `alt_m` | float | 5.0 | Target altitude in metres AGL.  Clamped to 60 m by the companion app. |

ACK: `{"ack": "takeoff", "result": "ok", "seq": 1}`

### `patrol`

```json
{
  "cmd": "patrol",
  "args": {
    "waypoints": [
      {"lat": 36.1, "lon": -105.2, "alt_m": 30.0, "hold_s": 0.0},
      {"lat": 36.2, "lon": -105.3, "alt_m": 30.0, "hold_s": 5.0}
    ]
  },
  "seq": 2
}
```

Each waypoint: `lat` (float), `lon` (float), `alt_m` (float), `hold_s` (float, default 0).

### `return_to_home`

```json
{"cmd": "return_to_home", "args": {}, "seq": 3}
```

### `play_deterrent`

```json
{"cmd": "play_deterrent", "args": {"tone_hz": 12000, "duration_s": 6.0}, "seq": 4}
```

Note: Mavic Air 2 has no onboard speaker.  The companion app logs the request
and optionally routes audio to a paired Bluetooth speaker.

### `capture_visual_clip`

```json
{"cmd": "capture_visual_clip", "args": {"duration_s": 10.0}, "seq": 5}
```

ACK includes `data.path` with the local file path on the device.

### `get_state`

```json
{"cmd": "get_state", "args": {}, "seq": 6}
```

ACK includes `data` with a `DroneStateSnapshot` (see JSON Schema below).

---

## MQTT Topics

| Topic | Direction | QoS | Retained | Description |
|---|---|---|---|---|
| `skyherd/drone/cmd/*` | backend → app | 1 | no | Commands (alternative transport) |
| `skyherd/drone/state/ios` | app → broker | 0 | yes | Latest state snapshot |
| `skyherd/drone/ack/ios` | app → broker | 1 | no | ACKs for MQTT-sourced commands |
| `skyherd/drone/status/ios` | app → broker | 1 | yes | `"online"` / `"offline"` (LWT) |

---

## Error Codes

| Code | Meaning |
|---|---|
| `E_DJI_NOT_READY` | DJI SDK not registered or aircraft not connected |
| `E_GEOFENCE_REJECT` | One or more waypoints are outside the loaded geofence polygon |
| `E_BATTERY_LOW` | Battery below 25% floor; takeoff denied |
| `E_WIND_CEILING` | Wind speed at or above 21 kt ceiling; takeoff denied |
| `E_TIMEOUT` | Companion app did not receive/execute the command within 30 s |
| `E_UNKNOWN_CMD` | `cmd` field does not match any known command |

---

## JSON Schema

The following schema validates both command and ACK envelopes.
Used by `tests/hardware/test_mavic_protocol.py`.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$defs": {
    "Waypoint": {
      "type": "object",
      "required": ["lat", "lon", "alt_m"],
      "properties": {
        "lat":    {"type": "number"},
        "lon":    {"type": "number"},
        "alt_m":  {"type": "number", "minimum": 0, "maximum": 120},
        "hold_s": {"type": "number", "minimum": 0}
      }
    },
    "DroneStateSnapshot": {
      "type": "object",
      "required": ["armed", "in_air", "altitude_m", "battery_pct", "mode", "lat", "lon"],
      "properties": {
        "armed":       {"type": "boolean"},
        "in_air":      {"type": "boolean"},
        "altitude_m":  {"type": "number", "minimum": 0},
        "battery_pct": {"type": "number", "minimum": 0, "maximum": 100},
        "mode":        {"type": "string"},
        "lat":         {"type": "number", "minimum": -90, "maximum": 90},
        "lon":         {"type": "number", "minimum": -180, "maximum": 180}
      }
    },
    "CommandArgs": {
      "type": "object"
    },
    "DroneCommand": {
      "type": "object",
      "required": ["cmd", "args", "seq"],
      "properties": {
        "cmd": {
          "type": "string",
          "enum": ["takeoff", "patrol", "return_to_home", "play_deterrent",
                   "capture_visual_clip", "get_state"]
        },
        "args": {"$ref": "#/$defs/CommandArgs"},
        "seq":  {"type": "integer", "minimum": 0}
      }
    },
    "DroneAck": {
      "type": "object",
      "required": ["ack", "result", "seq"],
      "properties": {
        "ack":     {"type": "string"},
        "result":  {"type": "string", "enum": ["ok", "error"]},
        "seq":     {"type": "integer", "minimum": 0},
        "message": {"type": "string"},
        "data":    {"oneOf": [{"type": "null"}, {"type": "object"}]}
      }
    }
  }
}
```

---

## Authentication

- **Dev mode** (current): open WebSocket, no auth.
- **Prod mode** (future work): TLS MQTT (`mqtts://`) + per-device JWT token passed
  in MQTT CONNECT `username`/`password`.  Companion apps obtain tokens via a
  one-time device-pairing flow on the SkyHerd dashboard.

---

## Sequence Diagram

```
Laptop (Python)          iPhone (Swift)
    |                         |
    |--- connect WebSocket --->|
    |<--- TCP accept ----------|
    |                         |
    |--- {"cmd":"get_state",  |
    |     "args":{},"seq":1}->|
    |                         |--- DJIBridge.state() --->
    |                         |<-- DroneStateSnapshot ---
    |<-- {"ack":"get_state",  |
    |     "result":"ok",      |
    |     "seq":1,"data":{…}} |
    |                         |
    |--- {"cmd":"takeoff",    |
    |     "args":{"alt_m":5}, |
    |     "seq":2} ---------->|
    |                         |-- SafetyGuards.check() -->
    |                         |-- DJIBridge.takeoff() --->
    |<-- {"ack":"takeoff",    |
    |     "result":"ok",      |
    |     "seq":2} -----------|
```
