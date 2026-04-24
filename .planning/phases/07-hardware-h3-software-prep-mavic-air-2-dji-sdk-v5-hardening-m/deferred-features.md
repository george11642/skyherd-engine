# Deferred features — Phase 7

Items surfaced during Phase 7 that are too scope-creeping or
hardware-dependent to complete before the 2026-04-26 submission. Each
entry includes severity, rationale, and the file/call-site to resume at.

---

## MEDIUM — iOS + Android full DJIWaypointV2Mission implementation

**Surfaced in:** 07-01 audit.
**Location:**
- `ios/SkyHerdCompanion/Sources/SkyHerdCompanion/DJIBridge.swift` —
  `gotoLocation(_:_:_:)` currently uses `fc.startGoHome` as placeholder.
- `android/SkyHerdCompanion/app/src/main/kotlin/com/skyherd/companion/DroneControl.kt`
  — `cmdGoto(args, seq)` stubs ACK-ok without SDK call.

**Why deferred:** Real `DJIWaypointV2Mission` integration requires:
1. `DJIWaypointV2Mission.Builder` construction per waypoint.
2. `WaypointV2MissionOperator.loadMission`/`uploadMission`/
   `startMission` async state machine.
3. Mission-end callbacks and interruption handling.
4. Physical-drone validation to catch edge cases (mission-abort on
   GPS loss, wind gust, geofence intersection).

Estimated effort: 1 full day + drone time. Not available in the
pre-submission window. Current stubs work because the Python-side
`MavicAdapter` failover logic (07-02) and recorded-packet replay
(07-04) exercise the JSON path end-to-end without needing real
waypoint upload.

**Resume:** after 2026-04-26 submission, with Mavic Air 2 in hand.

---

## MEDIUM — Android MQTT sequence-number dedupe window

**Surfaced in:** 07-01 audit.
**Location:** `android/SkyHerdCompanion/.../DroneControl.kt` — `handleCommand`
processes every incoming MQTT message without checking for prior `seq`.

**Why deferred:** MQTT broker is configured for QoS 1 (at-least-once
delivery), so retries are possible but rare. Real-world impact is
limited: a double-takeoff would be caught by DJI SDK's own "already
airborne" rejection, and most other commands are idempotent. iOS
already has a 256-entry `seenSeqs` set — we should mirror it on
Android, but it's not blocking.

**Resume:** mirror the `iOS/CommandRouter.seenSeqs` pattern in
`DroneControl.handleCommand` — add a `LinkedHashSet<Int>(256)` with
LRU eviction.

---

## LOW — iOS accessory speaker playback for deterrent tone

**Surfaced in:** 07-01 audit.
**Location:** `ios/SkyHerdCompanion/.../DJIBridge.swift` —
`playTone(hz:ms:)` currently logs only.

**Why deferred:** Mavic Air 2 has no onboard speaker. Adding Bluetooth
speaker support requires:
1. `ExternalAccessory` framework integration.
2. `AVAudioSession` configuration to route to the paired accessory.
3. Signal generator (sine wave) for the requested frequency.
4. Per-device tuning (different BT speakers respond differently to
   12 kHz tones).

The ground-side speaker bridge (`src/skyherd/edge/speaker_bridge.py`
from Phase 6) already covers the demo use case — a paired BT speaker
on the ranch vehicle plays the deterrent tone. Adding it to the drone
via the mobile app is a polish item, not a demo gate.

**Resume:** Post-hackathon polish — pair a small BT speaker with an
iOS test device, implement `playTone` via `AVAudioEngine.attach` +
`AVAudioSourceNode`.

---

_This file is updated incrementally as each Phase 7 plan executes.
Entries are added, not removed — if an item graduates from "deferred"
to "shipped", flip it to a note like "**RESOLVED in 07-02**" rather
than deleting._
