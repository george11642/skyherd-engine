# Phase 8 — Deferred Features

Items intentionally left out of Phase 8 that require real hardware or
future iteration. None block the hackathon submission — the software
path is complete.

## Hardware-gated (require real RAK3172 / gateway)

- [ ] **LoRaWAN FUOTA OTA** — Fragmented Data Block Transport + McClassC
  multicast session. Firmware has a sign-post block in
  `hardware/collar/firmware/src/main.cpp` under `#ifdef OTA_ENABLED`
  with three TODO lines (AT command, session management, fragment choice).
  Unblocks when a bench-top RAK3172 + gateway are available.
- [ ] **BLE DFU fallback** — RAK RUI3 bootloader advertises a DFU
  service on reset; ESP32 alt uses `esp_ota_*` over GATT. Demo-quality
  only (requires phone within 10 m). Sign-posted in same firmware block.
- [ ] **Real-antenna range test** — characterise US915 SF7 / SF10 range
  with the 3 dBi whip vs the ranch topography. Expected: ~3 km
  line-of-sight, ~1 km through juniper cover.

## Integration-gated (need live broker in CI)

- [ ] **MQTT integration real-broker test** — end-to-end test against
  a live Mosquitto + ChirpStack in CI. Phase 6's H2 `hardware-demo-sim`
  docker-compose stack already does this pattern; add a ChirpStack
  service + a fake uplink pump, assert a dashboard SSE event is
  emitted. Remains unit-tested in-process via
  `tests/hardware/test_h4_end_to_end.py` (5 tests, all green).
- [ ] **ChirpStack MQTT client integration test** — `ChirpStackMqttClient`
  in `chirpstack_bridge.py` is marked `# pragma: no cover` because
  exercising it needs a real broker. Covered by runbook Step 7.

## Post-MVP features

- [ ] **Geofence-driven uplink cadence** — drop interval to 60 s when a
  cow is near a known fence breach-point, raise to 1 h in deep pasture.
  Requires a downlink protocol spec; touches Port 1 (interval) logic
  in firmware `handle_downlink`.
- [ ] **Multi-region antenna stocking** — EU868 / AS923 / AU915
  variants. Not cross-border legal; add to BOM on demand when
  deploying outside the US.
- [ ] **Optional ESP32 coprocessor** — adds BLE OTA, edge ML, richer
  sensor fusion. Currently a BOM footnote; firmware would need an
  `#ifdef HAS_COPROCESSOR` branch.

## Open questions

- What cadence does the dashboard's SSE throttle at when 100 collars
  all uplink at 15 min cadence? Currently untested at scale; defer to
  a Phase 10+ load test.
- ChirpStack v4's `gatewayTime` field is optional — some integrations
  omit it. Our parser falls back to `time.time()` in that case; is
  that an acceptable replay hazard? (Bridge `ts_provider` hook exists
  to inject a deterministic timestamp; only the raw `rx_ts` is touched
  by wall-clock fallback.)
