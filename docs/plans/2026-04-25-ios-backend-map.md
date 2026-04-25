# SkyHerd iOS Backend Map — FastAPI Surface for SkyHerdRancher

> Generated: 2026-04-25  
> Source files read: `src/skyherd/server/app.py`, `events.py`, `live.py`, `memory_api.py`, `drone_control.py`

---

## 1. Base URL & Auth

- Default: `http://localhost:8000`
- No authentication headers required (no cookies, no bearer tokens)
- CORS: allowed origins are `http://localhost:5173`, `http://localhost:3000`, `http://localhost:8000` (dev defaults) or overridden via `SKYHERD_CORS_ORIGINS` env var
- **iOS Simulator note**: Simulator targets `localhost:8000` — this is already in the CORS allowlist. No CORS changes needed for Simulator. A real device on the same Wi-Fi must set `SKYHERD_CORS_ORIGINS` to include the device's access URL.
- CORS allows: `GET`, `POST`, `OPTIONS`; headers: `Content-Type`, `Accept`, `Cache-Control`, `Last-Event-ID`
- `allow_credentials=False` — no cookie-based auth

---

## 2. REST Endpoints (All Confirmed — Read from Code)

### 2.1 Health

```
GET /health
Response 200:
  { "status": "ok", "ts": "1745200000.123" }
```

Swift struct:
```swift
struct HealthResponse: Codable {
    let status: String
    let ts: String
}
```

---

### 2.2 World Snapshot

```
GET /api/snapshot
Response 200: WorldSnapshot JSON (see §4.1)
```

No query params. Returns full world state including cows, drone, predators, paddocks, water tanks, weather.

---

### 2.3 Agent Statuses

```
GET /api/agents
Response 200:
  { "agents": [AgentStatus], "ts": Double }
```

Swift struct:
```swift
struct AgentsResponse: Codable {
    let agents: [AgentStatus]
    let ts: Double
}

struct AgentStatus: Codable {
    let name: String
    let sessionId: String      // "sess_mock_fencelinedispatcher" or real sess_* id
    let state: String          // "active" | "idle"
    let lastWake: Double?
    let cumulativeTokensIn: Int
    let cumulativeTokensOut: Int
    let cumulativeCostUsd: Double

    enum CodingKeys: String, CodingKey {
        case name, state
        case sessionId = "session_id"
        case lastWake = "last_wake"
        case cumulativeTokensIn = "cumulative_tokens_in"
        case cumulativeTokensOut = "cumulative_tokens_out"
        case cumulativeCostUsd = "cumulative_cost_usd"
    }
}
```

Agent names (6 total, confirmed from `AGENT_NAMES` in `events.py`):
- `FenceLineDispatcher`
- `HerdHealthWatcher`
- `PredatorPatternLearner`
- `GrazingOptimizer`
- `CalvingWatch`
- `CrossRanchCoordinator`

---

### 2.4 Attestation Ledger

```
GET /api/attest?since_seq=<int>        (default 0, ge=0)
Response 200:
  { "entries": [AttestEntry], "ts": Double }
  Max 50 entries returned.

POST /api/attest/verify
Response 200:
  { "valid": Bool, "total": Int, "reason": String? }
  (mock mode: { "valid": true, "total": 0, "reason": "mock" })

GET /api/attest/by-hash/<hash_hex>
  - 400 if hash_hex invalid (non-hex, >128 chars)
  - 404 if not found
Response 200:
  { "target": String, "chain": [AttestEntry], "ts": Double }

GET /api/attest/pair/<memver_id>
  - 400 if memver_id invalid
  - 404 if not found
Response 200:
  { "memver_id": String, "ledger_entry": AttestEntry, "memver": MemverInfo, "ts": Double }
```

Swift structs:
```swift
struct AttestResponse: Codable {
    let entries: [AttestEntry]
    let ts: Double
}

struct AttestEntry: Codable, Identifiable {
    var id: Int { seq }
    let seq: Int
    let tsIso: String
    let source: String
    let kind: String
    let payloadJson: String
    let prevHash: String
    let eventHash: String
    let signature: String
    let pubkey: String
    let memverId: String?

    enum CodingKeys: String, CodingKey {
        case seq, source, kind, signature, pubkey
        case tsIso = "ts_iso"
        case payloadJson = "payload_json"
        case prevHash = "prev_hash"
        case eventHash = "event_hash"
        case memverId = "memver_id"
    }
}

struct VerifyResult: Codable {
    let valid: Bool
    let total: Int
    let reason: String?
}

struct AttestByHashResponse: Codable {
    let target: String
    let chain: [AttestEntry]
    let ts: Double
}

struct AttestPairResponse: Codable {
    let memverId: String
    let ledgerEntry: AttestEntry
    let memver: MemverInfo
    let ts: Double

    enum CodingKeys: String, CodingKey {
        case memverId = "memver_id"
        case ledgerEntry = "ledger_entry"
        case memver, ts
    }
}

struct MemverInfo: Codable {
    let id: String
    let agent: String?
    let contentSha256: String?
    let path: String?

    enum CodingKeys: String, CodingKey {
        case id, agent, path
        case contentSha256 = "content_sha256"
    }
}
```

---

### 2.5 Memory API

```
GET /api/memory/<agent>?path_prefix=<string>
  - 404 if agent not in AGENT_NAMES
  - 503 if no store registered for agent
Response 200:
  { "agent": String, "memory_store_id": String?, "entries": [MemoryEntry], 
    "prefixes": [String]?, "ts": Double }

GET /api/memory/<agent>/versions
  - 404 if agent not in AGENT_NAMES
Response 200:
  { "agent": String, "memory_store_id": String?, "entries": [MemoryEntry], "ts": Double }
```

Swift structs:
```swift
struct MemoryResponse: Codable {
    let agent: String
    let memoryStoreId: String?
    let entries: [MemoryEntry]
    let prefixes: [String]?
    let ts: Double

    enum CodingKeys: String, CodingKey {
        case agent, entries, prefixes, ts
        case memoryStoreId = "memory_store_id"
    }
}

struct MemoryEntry: Codable, Identifiable {
    var id: String { memoryId }
    let memoryId: String
    let memoryVersionId: String
    let memoryStoreId: String
    let path: String
    let contentSha256: String
    let contentSizeBytes: Int?
    let createdAt: String
    let operation: String?

    enum CodingKeys: String, CodingKey {
        case path, operation
        case memoryId = "memory_id"
        case memoryVersionId = "memory_version_id"
        case memoryStoreId = "memory_store_id"
        case contentSha256 = "content_sha256"
        case contentSizeBytes = "content_size_bytes"
        case createdAt = "created_at"
    }
}
```

---

### 2.6 Neighbor Handoff Log

```
GET /api/neighbors
Response 200:
  { "entries": [NeighborEntry], "ts": Double }
```

Swift struct:
```swift
struct NeighborsResponse: Codable {
    let entries: [NeighborEntry]
    let ts: Double
}

struct NeighborEntry: Codable {
    let direction: String        // "inbound" | "outbound"
    let fromRanch: String
    let toRanch: String
    let species: String
    let sharedFence: String
    let confidence: Double
    let ts: Double
    let attestationHash: String

    enum CodingKeys: String, CodingKey {
        case direction, species, confidence, ts
        case fromRanch = "from_ranch"
        case toRanch = "to_ranch"
        case sharedFence = "shared_fence"
        case attestationHash = "attestation_hash"
    }
}
```

---

### 2.7 Vet Intake

```
GET /api/vet-intake/<intake_id>
  - 400 if intake_id fails regex
  - 404 if file not found
Response 200: text/markdown body
```

Swift: returns `String` (raw Markdown). Render with `Text` + AttributedString or a Markdown-capable view.

---

### 2.8 Ambient Driver Control

```
POST /api/ambient/speed
  Body: { "speed": Double }   (0.0 ≤ speed ≤ 120.0)
  - 404 if ambient driver not attached
Response 200: { "speed": Double }

POST /api/ambient/next
  No body
  - 404 if ambient driver not attached
Response 200: { "skipped": String? }   // name of scenario that was skipped
```

NOTE: These endpoints exist but have no UI affordance in the shipped dashboard. The iOS app DOES need `/api/ambient/speed` for the speed slider and `/api/ambient/next` for scenario skip. They require the live server started with `make dashboard` (not mock mode).

---

### 2.9 Manual Drone Control (NOT needed for iOS viewer)

```
POST /api/drone/{arm|disarm|takeoff|rtl|land|estop}
Requires header: X-Manual-Override-Token: <token>
```

These are operator-only endpoints for laptop drone control. The iOS app should NOT expose these. They are listed here for completeness.

---

### 2.10 Metrics & Webhooks (iOS irrelevant)

- `GET /metrics` — Prometheus text, not needed in iOS
- `POST /webhooks/managed-agents` — agent mesh webhook, not needed in iOS

---

## 3. SSE Event Stream

```
GET /events
Content-Type: text/event-stream
```

Each event:
```
event: <event_type>
data: <json_payload>
```

Max 100 concurrent connections (returns 429 if exceeded). Header `X-Accel-Buffering: no` is set.

### 3.1 Complete Event Type Registry

Confirmed from `web/src/lib/sse.ts` and `events.py`:

| Event Type | Interval | Source |
|---|---|---|
| `world.snapshot` | ~2s | `_snapshot_loop` |
| `cost.tick` | ~1s | `_cost_loop` |
| `attest.append` | ~3s (poll) | `_attest_loop` |
| `agent.log` | ~0.8s (mock) | `_mock_agent_log_loop` |
| `vet_intake.drafted` | ~5s (poll) | `_vet_intake_loop` |
| `scenario.active` | on scenario start | `AmbientDriver` |
| `scenario.ended` | on scenario end | `AmbientDriver` |
| `memory.written` | on write | mesh emit |
| `memory.read` | on read | mesh emit |
| `neighbor.alert` | on inbound cross-ranch | `CrossRanchMesh` |
| `neighbor.handoff` | after pre-position | `CrossRanchMesh` |
| `drone.manual_override` | on drone API call | `drone_control` |
| `fence.breach` | (MQTT passthrough, inferred) | MQTT bus |
| `drone.update` | (MQTT passthrough, inferred) | MQTT bus |

Note: `fence.breach` and `drone.update` appear in the SSE client registry but are emitted by MQTT bus passthrough — they are received in live mode, not mock mode.

---

### 3.2 Per-Event JSON Schemas

#### `world.snapshot`
```swift
struct WorldSnapshot: Codable {
    let ts: Double
    let simTimeS: Double
    let clockIso: String
    let isNight: Bool
    let weather: Weather
    let cows: [Cow]
    let predators: [Predator]
    let drone: Drone
    let paddocks: [Paddock]
    let waterTanks: [WaterTank]

    enum CodingKeys: String, CodingKey {
        case ts, cows, predators, drone, paddocks, weather
        case simTimeS = "sim_time_s"
        case clockIso = "clock_iso"
        case isNight = "is_night"
        case waterTanks = "water_tanks"
    }
}

struct Weather: Codable {
    let conditions: String   // "clear"|"cloudy"|"storm"
    let tempF: Double
    let windKt: Double
    let humidityPct: Double

    enum CodingKeys: String, CodingKey {
        case conditions
        case tempF = "temp_f"
        case windKt = "wind_kt"
        case humidityPct = "humidity_pct"
    }
}

struct Cow: Codable, Identifiable {
    let id: String
    let tag: String?
    let pos: [Double]          // [x, y] in normalized 0.0–1.0 coords
    let bcs: Double?           // body condition score 1–9
    let state: String?         // "grazing"|"resting"|"walking"|"sick"|"calving"|"labor"
    let headingDeg: Double?

    enum CodingKeys: String, CodingKey {
        case id, tag, pos, bcs, state
        case headingDeg = "heading_deg"
    }
}

struct Predator: Codable, Identifiable {
    let id: String
    let pos: [Double]          // [x, y] normalized
    let species: String?       // "coyote"
    let threatLevel: String?   // "low"|"medium"|"high"

    enum CodingKeys: String, CodingKey {
        case id, pos, species
        case threatLevel = "threat_level"
    }
}

struct Drone: Codable {
    let lat: Double?
    let lon: Double?
    let altM: Double?
    let state: String?         // "idle"|"patrol"|"investigating"
    let batteryPct: Double?

    enum CodingKeys: String, CodingKey {
        case lat, lon, state
        case altM = "alt_m"
        case batteryPct = "battery_pct"
    }
}

struct Paddock: Codable, Identifiable {
    let id: String
    let bounds: [Double]       // [minX, minY, maxX, maxY] normalized
    let foragePct: Double

    enum CodingKeys: String, CodingKey {
        case id, bounds
        case foragePct = "forage_pct"
    }
}

struct WaterTank: Codable, Identifiable {
    let id: String
    let pos: [Double]          // [x, y] normalized
    let levelPct: Double

    enum CodingKeys: String, CodingKey {
        case id, pos
        case levelPct = "level_pct"
    }
}
```

#### `cost.tick`
```swift
struct CostTick: Codable {
    let ts: Double
    let seq: Int
    let agents: [AgentCostEntry]
    let allIdle: Bool
    let ratePerHrUsd: Double
    let totalCumulativeUsd: Double

    enum CodingKeys: String, CodingKey {
        case ts, seq, agents
        case allIdle = "all_idle"
        case ratePerHrUsd = "rate_per_hr_usd"
        case totalCumulativeUsd = "total_cumulative_usd"
    }
}

struct AgentCostEntry: Codable {
    let name: String
    let state: String          // "active"|"idle"
    let costDeltaUsd: Double
    let cumulativeCostUsd: Double
    let tokensIn: Int
    let tokensOut: Int

    enum CodingKeys: String, CodingKey {
        case name, state
        case costDeltaUsd = "cost_delta_usd"
        case cumulativeCostUsd = "cumulative_cost_usd"
        case tokensIn = "tokens_in"
        case tokensOut = "tokens_out"
    }
}
```

#### `attest.append`
Same shape as `AttestEntry` above.

#### `agent.log`
```swift
struct AgentLogEvent: Codable {
    let ts: Double
    let agent: String
    let state: String?
    let message: String?
    let level: String?
    let tool: String?
    let line: String?
    let seq: Int?
}
```

#### `vet_intake.drafted`
```swift
struct VetIntakeDraftedEvent: Codable {
    let id: String            // e.g. "A014_20260422T153200Z"
    let cowTag: String
    let severity: String      // "escalate"
    let path: String
    let ts: Double

    enum CodingKeys: String, CodingKey {
        case id, severity, path, ts
        case cowTag = "cow_tag"
    }
}
```

#### `scenario.active`
```swift
struct ScenarioActiveEvent: Codable {
    let name: String           // "coyote"|"sick_cow"|"water_drop"|"calving"|"storm"|
                               // "wildfire"|"rustling"|"cross_ranch_coyote"
    let passIdx: Int
    let speed: Double
    let startedAt: String      // ISO 8601

    enum CodingKeys: String, CodingKey {
        case name, speed
        case passIdx = "pass_idx"
        case startedAt = "started_at"
    }
}
```

#### `scenario.ended`
```swift
struct ScenarioEndedEvent: Codable {
    let name: String
    let passIdx: Int
    let outcome: String        // "ok"|"cancelled"|error string
    let startedAt: String
    let endedAt: String

    enum CodingKeys: String, CodingKey {
        case name, outcome
        case passIdx = "pass_idx"
        case startedAt = "started_at"
        case endedAt = "ended_at"
    }
}
```

#### `memory.written` / `memory.read`
```swift
struct MemoryWrittenEvent: Codable {
    let agent: String
    let memoryStoreId: String
    let memoryId: String
    let memoryVersionId: String
    let contentSha256: String
    let path: String

    enum CodingKeys: String, CodingKey {
        case agent, path
        case memoryStoreId = "memory_store_id"
        case memoryId = "memory_id"
        case memoryVersionId = "memory_version_id"
        case contentSha256 = "content_sha256"
    }
}
```

#### `neighbor.alert`
```swift
struct NeighborAlertEvent: Codable {
    let fromRanch: String
    let toRanch: String
    let species: String
    let sharedFence: String
    let confidence: Double
    let ts: Double
    let attestationHash: String

    enum CodingKeys: String, CodingKey {
        case species, confidence, ts
        case fromRanch = "from_ranch"
        case toRanch = "to_ranch"
        case sharedFence = "shared_fence"
        case attestationHash = "attestation_hash"
    }
}
```

#### `neighbor.handoff`
```swift
struct NeighborHandoffEvent: Codable {
    let fromRanch: String
    let toRanch: String
    let species: String
    let sharedFence: String
    let responseMode: String
    let toolCalls: [String]
    let rancherPaged: Bool
    let ts: Double

    enum CodingKeys: String, CodingKey {
        case species, ts
        case fromRanch = "from_ranch"
        case toRanch = "to_ranch"
        case sharedFence = "shared_fence"
        case responseMode = "response_mode"
        case toolCalls = "tool_calls"
        case rancherPaged = "rancher_paged"
    }
}
```

---

## 4. Map/World Geometry

### 4.1 Coordinate System

The world snapshot uses **normalized 0.0–1.0 coordinates**, not real GPS lat/lon. The `pos` field on cows, predators, and water_tanks is `[x, y]` where `[0,0]` is top-left, `[1,1]` is bottom-right.

The drone is an exception — it carries real GPS `lat`/`lon` plus `alt_m`.

The `paddocks.bounds` field is `[minX, minY, maxX, maxY]` in normalized space.

**For the iOS MapKit view**: normalized coordinates must be projected onto a fake coordinate space. Recommended: use a fixed bounding box (e.g. `lat: 34.12 ± 0.05`, `lon: -106.45 ± 0.05`) and linearly map `[0,1]` → `[minLat, maxLat]` / `[minLon, maxLon]`. The web SPA uses a Canvas 2D approach — the iOS app can either match that with a custom `UIViewRepresentable` canvas, or use MapKit with fake lat/lon projections.

### 4.2 Ranch Geometry (Mock)

4 paddocks: `north [0,0,0.5,0.5]`, `south [0.5,0,1,0.5]`, `east [0.5,0.5,1,1]`, `west [0,0.5,0.5,1]`

2 water tanks: `tank_a [0.25, 0.25]`, `tank_b [0.75, 0.75]`

12 cows (mock), 0–1 predators (20% chance in mock), 1 drone.

---

## 5. Static Assets

- No sprite images are served by FastAPI. The web SPA renders everything via **Canvas 2D** (no image sprites in the public directory — confirmed: `web/public/` contains only `fonts/`, `manifest.json`, and replay JSON files).
- The iOS app should draw entities using Core Graphics / SwiftUI shapes + SF Symbols, matching the web color palette (see §6).
- Fonts: `Inter` (variable) and `Fraunces` (variable) are used in the web SPA. iOS app should use system fonts (SF Pro) to avoid bundling font files.

---

## 6. Color Palette (from `web/src/index.css`)

| Token | Value | Purpose |
|---|---|---|
| `bg-0` | `rgb(10,12,16)` | Deep background |
| `bg-1` | `rgb(16,19,25)` | Card background |
| `bg-2` | `rgb(24,28,36)` | Elevated surface |
| `line` | `rgb(38,45,58)` | Divider/border |
| `text-0` | `rgb(236,239,244)` | Primary text |
| `text-1` | `rgb(168,180,198)` | Secondary text |
| `text-2` | `rgb(110,122,140)` | Tertiary/placeholder |
| `accent-sage` | `rgb(148,176,136)` | Healthy cow, paddock fill |
| `accent-dust` | `rgb(210,178,138)` | Watch/caution, earthy |
| `accent-thermal` | `rgb(255,143,60)` | Thermal/alert |
| `accent-sky` | `rgb(120,180,220)` | Drone, sky blue |
| `warn` | `rgb(240,195,80)` | Warning/amber |
| `danger` | `rgb(224,100,90)` | Sick/predator/threat |
| `ok` | `rgb(120,190,140)` | Verified/safe |

Entity colors (from `RanchMap.tsx`):
- Healthy cow: `#94b088` (sage)
- Watch cow: `#d2b28a` (dust)
- Sick cow: `#e0645a` (danger)
- Calving cow: `#78b4dc` (sky)
- Drone: `#78b4dc` (sky)
- Predator: `#e0645a` (danger)

---

## 7. Scenarios Registry

8 scenarios confirmed from `src/skyherd/scenarios/__init__.py`:

| Key | Display Name |
|---|---|
| `coyote` | Coyote at Fence |
| `sick_cow` | Sick Cow |
| `water_drop` | Water Tank Drop |
| `calving` | Calving |
| `storm` | Storm Incoming |
| `wildfire` | Wildfire Alert |
| `rustling` | Rustling Detected |
| `cross_ranch_coyote` | Cross-Ranch Coyote |

The ambient driver rotates through all 8 in order. The 5 "hero" scenarios documented in CLAUDE.md are: coyote, sick_cow, water_drop, calving, storm.

---

## 8. Missing/Proposed Endpoints

The following endpoints are **not present** in the current backend but would be useful for the iOS app. The implementation agents should add these minimal FastAPI additions:

### 8.1 `GET /api/scenarios` (PROPOSED)
Returns list of available scenario names so the iOS picker doesn't need to hard-code them.

```python
@app.get("/api/scenarios")
async def api_scenarios():
    from skyherd.scenarios import SCENARIOS
    return JSONResponse(content={"scenarios": list(SCENARIOS.keys())})
```

### 8.2 `GET /api/status` (PROPOSED)
Returns current ambient driver state for the iOS "Live" tab initial load.

```python
@app.get("/api/status")
async def api_status():
    driver = getattr(app.state, "ambient_driver", None)
    return JSONResponse(content={
        "active_scenario": driver.active_scenario if driver else None,
        "speed": driver.speed if driver else 1.0,
        "mock": use_mock,
    })
```

These two endpoints are small additions; flag them for the Wave A implementation agent to add to `src/skyherd/server/app.py`.
