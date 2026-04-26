# SkyHerdRancher iOS App — Design Document

> Generated: 2026-04-25  
> For: Anthropic "Built with Opus 4.7" hackathon — Sun Apr 26 2026 6pm EST target submission  
> Companion doc: `docs/plans/2026-04-25-ios-backend-map.md` (read this first for all backend schemas)

---

## Goal

Build a native SwiftUI iOS 17+ app (`ios/SkyHerdRancher/`) that is a **live viewer** for the SkyHerd FastAPI backend running on `localhost:8000`. The app connects to `/events` SSE stream, renders ranch state in real time, and surfaces the 5-agent mesh status, attestation ledger, and Wes alerts. It is a demo/judge-facing screen companion to the web SPA — judges can hold a phone next to the laptop to see the same simulation play out natively.

---

## Non-Goals

- No native simulation logic — all sim runs on the Python backend
- No Twilio/ElevenLabs integration (Wes calls come through as alert SSE events only)
- No DJI SDK / MQTT — that lives in `ios/SkyHerdCompanion/`; do NOT touch that directory
- No push notifications, background fetch, or offline mode
- No user accounts, auth, or persistence beyond a single UserDefaults key for base URL
- No iPad-specific layout (phone layout only; iPad can stretch)
- No App Store submission — demo build only
- No localization

---

## App Architecture

**Pattern**: SwiftUI iOS 17+, MVVM with `@Observable` macro (NOT `ObservableObject`). One root `AppState` actor owns the SSE connection and fans events to per-screen ViewModels. ViewModels are plain `@Observable` classes passed via initializer injection (no environment globals beyond `AppState`).

**Key design choices** (supported by Context7 + web search findings):

1. `@Observable` replaces `ObservableObject` — no `@Published`, no `@StateObject`/`@ObservedObject`. Views read properties directly; SwiftUI tracks access automatically.
2. `AppState` is created once at app entry as `@State private var appState = AppState()` and passed down via `.environment(appState)`.
3. Each screen ViewModel is created by the parent view that owns its tab, stored as `@State`.
4. SSE connection lives in `SSEClient` actor; AppState subscribes via `AsyncStream<SkyHerdEvent>` and routes by event type to each ViewModel's update method.
5. No Combine. Swift Concurrency (`async/await`, `AsyncStream`, `Task`) throughout.
6. No third-party dependencies except possibly one (see §8 Networking).

---

## Folder Structure

```
ios/SkyHerdRancher/
├── SkyHerdRancher.xcodeproj/
│   └── project.pbxproj
├── SkyHerdRancher/
│   ├── App/
│   │   ├── SkyHerdRancherApp.swift        # @main, creates AppState, root TabView
│   │   └── AppState.swift                 # @Observable, owns SSEClient, routes events
│   ├── Models/
│   │   ├── WorldModels.swift              # WorldSnapshot, Cow, Predator, Drone, Paddock, WaterTank, Weather
│   │   ├── AgentModels.swift              # AgentStatus, CostTick, AgentCostEntry, AgentLogEvent
│   │   ├── AttestModels.swift             # AttestEntry, AttestResponse, VerifyResult, AttestPairResponse
│   │   ├── MemoryModels.swift             # MemoryEntry, MemoryResponse
│   │   ├── ScenarioModels.swift           # ScenarioActiveEvent, ScenarioEndedEvent
│   │   ├── AlertModels.swift              # VetIntakeDraftedEvent, NeighborAlertEvent, NeighborHandoffEvent
│   │   └── SSEEvent.swift                 # SkyHerdEvent enum (typed union of all SSE event types)
│   ├── Networking/
│   │   ├── APIClient.swift                # actor: REST calls, JSON decode, error handling
│   │   ├── SSEClient.swift                # actor: URLSession AsyncBytes, line parsing, reconnect
│   │   └── Configuration.swift           # BaseURL, UserDefaults key, launch arg override
│   ├── Features/
│   │   ├── Live/
│   │   │   ├── LiveView.swift             # Tab 1: scenario picker, play/pause, speed, event feed
│   │   │   └── LiveViewModel.swift        # @Observable: activeScenario, speed, recentEvents[]
│   │   ├── Map/
│   │   │   ├── MapView.swift              # Tab 2: MapKit ranch view
│   │   │   ├── RanchMapView.swift         # custom MapKit overlay drawing (UIViewRepresentable)
│   │   │   └── MapViewModel.swift         # @Observable: latest WorldSnapshot, breach pins
│   │   ├── Agents/
│   │   │   ├── AgentsView.swift           # Tab 3: 5-agent card grid
│   │   │   ├── AgentCardView.swift        # single agent card with cost sparkline
│   │   │   └── AgentsViewModel.swift      # @Observable: agentStatuses[], costHistory[]
│   │   ├── Alerts/
│   │   │   ├── AlertsView.swift           # Tab 4: Wes feed (vet intake + neighbor alerts)
│   │   │   └── AlertsViewModel.swift      # @Observable: alerts[], unreadCount
│   │   └── Ledger/
│   │       ├── LedgerView.swift           # Tab 5: attestation chain list + detail
│   │       ├── LedgerDetailView.swift     # hash viewer, chain ancestry
│   │       └── LedgerViewModel.swift      # @Observable: entries[], searchText, verifyResult
│   ├── DesignSystem/
│   │   ├── Colors.swift                   # SkyHerdColor enum/extension matching web palette
│   │   ├── Typography.swift               # font helpers (SF Pro, SF Mono)
│   │   └── EntityShapes.swift             # CowShape, DroneShape, PredatorShape (SwiftUI Shape)
│   └── Resources/
│       ├── Assets.xcassets/               # app icon, accent color
│       └── Info.plist
├── SkyHerdRancherTests/
│   ├── ModelDecodeTests.swift             # XCTest: decode sample JSON fixtures
│   ├── SSEClientTests.swift               # XCTest: line parser, event dispatch
│   ├── LiveViewModelTests.swift           # XCTest: state transitions
│   ├── LedgerViewModelTests.swift         # XCTest: search, verify
│   └── Fixtures/
│       ├── world_snapshot.json
│       ├── cost_tick.json
│       ├── attest_entry.json
│       └── agent_log.json
└── README.md                              # build & run instructions
```

---

## Screens

### Tab 1 — Live

**Purpose**: Control and observe the ambient scenario loop. Primary "wow" screen for demo.

**Key UI elements**:
- Top: scenario pill strip (8 pills: coyote, sick_cow, water_drop, calving, storm, wildfire, rustling, cross_ranch_coyote). Active scenario glows amber. Tap a pill → `POST /api/ambient/next` to skip to it (note: the API skips the current, not jumps to a specific one — match web SPA behavior).
- Narration banner: animated slide-in when `scenario.active` fires. Shows scenario name + icon. Fades after 4s or persists while active. Color-coded by scenario type.
- Speed slider: 1×–100× logarithmic. On change (debounced 300ms): `POST /api/ambient/speed` with `{"speed": value}`. Initial value fetched from `GET /api/status` on appear.
- Play/pause button: visual toggle only on iOS side (no pause endpoint exists on backend). When "paused", hide event feed updates (freeze last state). Note this to judges as UI-only.
- Live event feed: `ScrollView` with `LazyVStack`, newest event at top. Shows last 50 `agent.log` events. Each row: agent name chip (color-coded by agent), message text, relative timestamp.
- Cost ticker: bottom bar showing `rate_per_hr_usd` from `cost.tick` events. Green when all_idle, amber otherwise.

**Backend calls**:
- `GET /api/status` (proposed — see backend map §8.2) on appear for initial state
- `POST /api/ambient/speed` on slider change
- `POST /api/ambient/next` on scenario pill tap
- SSE: `scenario.active`, `scenario.ended`, `agent.log`, `cost.tick`

**State shape** (LiveViewModel):
```swift
@Observable class LiveViewModel {
    var activeScenario: String? = nil
    var speed: Double = 15.0
    var isPaused: Bool = false
    var recentEvents: [AgentLogEvent] = []   // capped at 50
    var costRate: Double = 0.0
    var allIdle: Bool = true
}
```

**Edge cases**:
- Backend not running: show "Connecting…" overlay with retry button
- `POST /api/ambient/speed` returns 404 (driver not attached): show toast "Speed control requires live mode"
- Speed slider rapid-fire: debounce 300ms to avoid overwhelming the server

---

### Tab 2 — Map

**Purpose**: Live ranch map showing cow herd, drone, predators, paddock overlays, fence lines, breach pins. Visual centerpiece.

**Key UI elements**:

Option A (recommended for hackathon speed): custom `Canvas`-based view (`UIViewRepresentable` wrapping `UIView` with `CADisplayLink`) mirroring the web SPA approach. This avoids MapKit coordinate projection complexity since world coords are normalized 0.0–1.0, not real GPS.

Option B: MapKit `Map` with fake lat/lon projection (more impressive on device but harder to implement correctly in time).

**Recommendation**: Use Option A for hackathon. Implement a SwiftUI `Canvas` view (`canvas { context, size in ... }`) which is native SwiftUI iOS 15+ and avoids UIKit bridging. Re-renders on each `world.snapshot` SSE event.

Layers (painter's algorithm, matching web SPA):
1. Paddock fills (color by forage_pct: green → amber → red)
2. Paddock labels (id, forage %)
3. Water tank circles (blue, level as ring fill)
4. Fence lines (simple boundary rect)
5. Cows (circle, color by health state: sage/dust/danger/sky)
6. Drone (triangle shape, sky blue, battery indicator)
7. Predators (red X or threat icon, ring for high threat)
8. Breach pins (if `neighbor.alert` received)
9. Weather overlay (bottom-left: icon + temp)
10. Scenario glow zone (amber tint on relevant paddock during active scenario)

**Backend calls**:
- `GET /api/snapshot` on appear (initial load before SSE catches up)
- SSE: `world.snapshot` (primary feed), `scenario.active`/`scenario.ended` (glow zone), `neighbor.alert` (breach pin)

**State shape** (MapViewModel):
```swift
@Observable class MapViewModel {
    var snapshot: WorldSnapshot? = nil
    var activeScenario: String? = nil
    var breachPins: [NeighborAlertEvent] = []  // cleared on scenario.ended
}
```

**Edge cases**:
- Empty snapshot: show "Waiting for sim data…" centered text over terrain background
- More than 20 cows: Canvas handles this fine (no performance issue)
- MapKit approach note: if using MapKit, use `Map` initializer with `MapCameraPosition` binding; use `Annotation` for cows/drone (custom view), `MapPolygon` for paddocks. Requires coordinate projection utility. Confidence HIGH for MapKit Annotation/MapPolygon API (confirmed Context7 + web search).

---

### Tab 3 — Agents

**Purpose**: Show the 5-agent mesh cards with current state, cumulative cost, token counts, and last decision.

**Key UI elements**:
- 2-column grid of 6 agent cards (FenceLineDispatcher, HerdHealthWatcher, PredatorPatternLearner, GrazingOptimizer, CalvingWatch, CrossRanchCoordinator)
- Each card:
  - Agent name (abbreviated on small screens)
  - State badge: `active` (amber pulse) / `idle` (gray)
  - Cumulative cost: `$0.0023`
  - Token bar: tokens_in / tokens_out as horizontal mini bar
  - Last log message: most recent `agent.log` entry for this agent (truncated to 2 lines)
  - Session ID (small mono text, shows `sess_*` to prove real platform registration)
  - Swift Charts sparkline (last 20 `cost_delta_usd` values) — use `Chart` from Swift Charts (iOS 16+)
- Tap card → sheet with full log history for that agent (filtered from `recentEvents`)

**Backend calls**:
- `GET /api/agents` on appear (initial state)
- SSE: `cost.tick` (state + cost updates), `agent.log` (last message per agent)

**State shape** (AgentsViewModel):
```swift
@Observable class AgentsViewModel {
    var agentStatuses: [String: AgentStatus] = [:]   // keyed by name
    var costHistory: [String: [Double]] = [:]         // agent → last 20 deltas
    var lastLogs: [String: AgentLogEvent] = [:]       // agent → most recent log
    var selectedAgent: String? = nil                  // for detail sheet
}
```

**Edge cases**:
- Missing agent in SSE: keep last known state
- Cost delta = 0 when idle: sparkline shows flat line (expected)

---

### Tab 4 — Alerts

**Purpose**: Feed of Wes-facing alerts (vet intakes, neighbor alerts, calving pages). Urgency badges. Acknowledge action.

**Key UI elements**:
- `List` of alert items, newest first
- Alert types:
  - `vet_intake.drafted`: cow tag, severity badge (red "ESCALATE"), "View Intake" button → sheet with Markdown rendered from `GET /api/vet-intake/<id>`
  - `neighbor.alert`: from/to ranch, species, confidence %, fence ID
  - `neighbor.handoff`: response mode, tool calls list, rancher_paged badge
- Urgency color coding: escalate = danger red, handoff = amber, alert = sky blue
- Swipe-to-acknowledge (local UI state only — no backend ack endpoint)
- Tab badge count: unread count (red circle on tab icon)
- Empty state: "No alerts — all clear" with green checkmark

**Backend calls**:
- `GET /api/neighbors` on appear (initial load)
- `GET /api/vet-intake/<id>` on "View Intake" tap (lazy load)
- SSE: `vet_intake.drafted`, `neighbor.alert`, `neighbor.handoff`

**State shape** (AlertsViewModel):
```swift
@Observable class AlertsViewModel {
    var alerts: [SkyHerdAlert] = []    // union type (see Models)
    var acknowledgedIds: Set<String> = []
    var unreadCount: Int { alerts.filter { !acknowledgedIds.contains($0.id) }.count }
}

enum SkyHerdAlert: Identifiable {
    case vetIntake(VetIntakeDraftedEvent)
    case neighborAlert(NeighborAlertEvent)
    case neighborHandoff(NeighborHandoffEvent)
    
    var id: String { ... }  // derived from event content
    var ts: Double { ... }
}
```

**Edge cases**:
- Vet intake markdown fetch fails: show inline error "Could not load intake document"
- Long alert lists: `List` handles virtualization automatically

---

### Tab 5 — Ledger

**Purpose**: Attestation chain viewer. Shows Ed25519-signed ledger entries, chain back to genesis, verify badge.

**Key UI elements**:
- `List` of ledger entries (paginated via `since_seq`, load-more at bottom)
- Each row: seq number, kind badge, source, truncated hash, ISO timestamp
- Search bar: filter by hash prefix or source name (local filter on loaded entries)
- "Verify Chain" button: `POST /api/attest/verify` → shows `VerifyResult` (green "VALID N entries" or red "INVALID")
- Tap row → `LedgerDetailView`:
  - Full hash (monospace, tap to copy)
  - Payload JSON (formatted, monospace)
  - Chain ancestry: calls `GET /api/attest/by-hash/<hash>` to show parent chain
  - If `memver_id` present: "Paired Memory Version" section with link to memory detail
  - Signature (truncated + "Copy" button)
- Kind color codes: `sensor.reading` blue, `cost.tick` gray, `fence.breach` red, `agent.wake` amber, `agent.sleep` gray

**Backend calls**:
- `GET /api/attest?since_seq=0` on appear, load-more increments `since_seq`
- `POST /api/attest/verify` on button tap
- `GET /api/attest/by-hash/<hash>` on detail view appear
- `GET /api/attest/pair/<memver_id>` for memver-linked entries
- SSE: `attest.append` (real-time new entries)

**State shape** (LedgerViewModel):
```swift
@Observable class LedgerViewModel {
    var entries: [AttestEntry] = []
    var searchText: String = ""
    var verifyResult: VerifyResult? = nil
    var isVerifying: Bool = false
    var lastSeq: Int = 0
    var isLoadingMore: Bool = false

    var filteredEntries: [AttestEntry] {
        guard !searchText.isEmpty else { return entries }
        return entries.filter {
            $0.eventHash.hasPrefix(searchText) ||
            $0.source.localizedCaseInsensitiveContains(searchText)
        }
    }
}
```

**Edge cases**:
- `since_seq` pagination: track `lastSeq`, append (not replace) on load-more
- SSE `attest.append` arrives: prepend to entries if not already present (check seq)
- Verify on empty ledger: show "0 entries verified (mock mode)"

---

## Data Models

All Codable Swift structs are specified in `docs/plans/2026-04-25-ios-backend-map.md` (§2–§3). The implementation agent should use those exact structs verbatim. Key notes:

- All `snake_case` JSON keys must use `CodingKeys` enum for Swift camelCase properties
- `Double` for all timestamps (Unix epoch seconds as `Double`, not `Date`)
- `[Double]` for `pos` and `bounds` arrays (not `CGPoint`/`CGRect` — keep as raw array until display time)
- Decode `ts` fields as `Double`, format for display using `Date(timeIntervalSince1970: ts)`
- Optional fields liberally (`?`) since mock vs live mode produces different field sets

---

## Networking Layer

### APIClient

```swift
actor APIClient {
    let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder

    init(baseURL: URL = Configuration.defaultBaseURL) {
        self.baseURL = baseURL
        self.session = URLSession.shared
        self.decoder = JSONDecoder()
        // no date decoding strategy needed — all dates are Double epoch or ISO strings
    }

    func get<T: Decodable>(_ path: String) async throws -> T
    func post<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T
    func postEmpty(_ path: String) async throws -> Data   // for endpoints with no typed response
}
```

Error model:
```swift
enum APIError: Error {
    case httpError(statusCode: Int, detail: String?)
    case decodingError(Error)
    case networkError(Error)
}
```

### SSEClient

```swift
actor SSEClient {
    private let url: URL
    private var task: URLSessionDataTask?
    private var continuation: AsyncStream<SkyHerdEvent>.Continuation?

    func events() -> AsyncStream<SkyHerdEvent>   // returns stream, starts connection
    func disconnect()

    // Internal: URLSession.shared.bytes(from: url) → iterate lines
    // Parse SSE format: accumulate "event:" and "data:" lines, dispatch on blank line
    // Reconnect with exponential backoff (1s → 2s → 4s → max 30s) on error
    // Respect Last-Event-ID header if server sends event IDs (currently it doesn't, but be ready)
}
```

**SSE line parsing** (pure Swift, no third-party library needed):
```
Lines are UTF-8. Parse spec:
- "event: <type>" → store event type
- "data: <json>" → store data
- "" (blank) → dispatch accumulated event, reset buffer
- ":" (comment) → ignore (keep-alive heartbeats)
```

Swift implementation using `URLSession.bytes`:
```swift
let (asyncBytes, response) = try await URLSession.shared.bytes(from: url)
var eventType = "message"
var dataBuffer = ""
for try await line in asyncBytes.lines {
    if line.hasPrefix("event:") {
        eventType = String(line.dropFirst(6)).trimmingCharacters(in: .whitespaces)
    } else if line.hasPrefix("data:") {
        dataBuffer += String(line.dropFirst(5)).trimmingCharacters(in: .whitespaces)
    } else if line.isEmpty && !dataBuffer.isEmpty {
        // dispatch eventType + dataBuffer
        eventType = "message"
        dataBuffer = ""
    }
}
```

Confidence: HIGH — `URLSession.bytes(from:)` and `.lines` are confirmed iOS 15+ API; `AsyncBytes.lines` is the correct property name.

### SkyHerdEvent (typed union)

```swift
enum SkyHerdEvent {
    case worldSnapshot(WorldSnapshot)
    case costTick(CostTick)
    case attestAppend(AttestEntry)
    case agentLog(AgentLogEvent)
    case vetIntakeDrafted(VetIntakeDraftedEvent)
    case scenarioActive(ScenarioActiveEvent)
    case scenarioEnded(ScenarioEndedEvent)
    case memoryWritten(MemoryWrittenEvent)
    case memoryRead(MemoryWrittenEvent)   // same shape
    case neighborAlert(NeighborAlertEvent)
    case neighborHandoff(NeighborHandoffEvent)
    case unknown(type: String, data: String)
}
```

### Configuration

```swift
enum Configuration {
    static var defaultBaseURL: URL {
        // 1. Check launch argument: -SkyHerdBaseURL http://192.168.1.5:8000
        if let arg = ProcessInfo.processInfo.arguments.first(where: { $0.hasPrefix("-SkyHerdBaseURL") }) { ... }
        // 2. Check UserDefaults
        if let stored = UserDefaults.standard.string(forKey: "skyherd_base_url") { ... }
        // 3. Default: localhost:8000
        return URL(string: "http://localhost:8000")!
    }
}
```

---

## State Management

`AppState` owns the SSEClient and fans out events:

```swift
@Observable class AppState {
    let apiClient: APIClient
    private let sseClient: SSEClient
    
    // Per-screen ViewModels (created once, held here)
    let liveVM: LiveViewModel
    let mapVM: MapViewModel
    let agentsVM: AgentsViewModel
    let alertsVM: AlertsViewModel
    let ledgerVM: LedgerViewModel

    var connectionState: ConnectionState = .disconnected  // .disconnected | .connecting | .connected | .error(String)

    func start() {
        Task {
            for await event in await sseClient.events() {
                await route(event)
            }
        }
    }

    @MainActor
    private func route(_ event: SkyHerdEvent) {
        switch event {
        case .worldSnapshot(let s):   mapVM.handle(s)
        case .costTick(let t):        agentsVM.handle(t)
        case .agentLog(let l):        agentsVM.handle(l); liveVM.handle(l)
        case .attestAppend(let a):    ledgerVM.handle(a)
        case .vetIntakeDrafted(let v): alertsVM.handle(v)
        case .neighborAlert(let n):   alertsVM.handle(n); mapVM.handle(n)
        case .neighborHandoff(let h): alertsVM.handle(h)
        case .scenarioActive(let s):  liveVM.handle(s); mapVM.handle(s)
        case .scenarioEnded(let s):   liveVM.handle(s); mapVM.handle(s)
        case .memoryWritten(let m):   agentsVM.handle(m)
        default: break
        }
    }
}
```

Root app:
```swift
@main struct SkyHerdRancherApp: App {
    @State private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(appState)
                .onAppear { appState.start() }
        }
    }
}
```

---

## Design System

### Colors (matching web SPA)

```swift
extension Color {
    // Backgrounds
    static let skhBg0 = Color(red: 10/255, green: 12/255, blue: 16/255)
    static let skhBg1 = Color(red: 16/255, green: 19/255, blue: 25/255)
    static let skhBg2 = Color(red: 24/255, green: 28/255, blue: 36/255)
    static let skhLine = Color(red: 38/255, green: 45/255, blue: 58/255)
    // Text
    static let skhText0 = Color(red: 236/255, green: 239/255, blue: 244/255)
    static let skhText1 = Color(red: 168/255, green: 180/255, blue: 198/255)
    static let skhText2 = Color(red: 110/255, green: 122/255, blue: 140/255)
    // Accents
    static let skhSage = Color(red: 148/255, green: 176/255, blue: 136/255)
    static let skhDust = Color(red: 210/255, green: 178/255, blue: 138/255)
    static let skhThermal = Color(red: 255/255, green: 143/255, blue: 60/255)
    static let skhSky = Color(red: 120/255, green: 180/255, blue: 220/255)
    static let skhWarn = Color(red: 240/255, green: 195/255, blue: 80/255)
    static let skhDanger = Color(red: 224/255, green: 100/255, blue: 90/255)
    static let skhOk = Color(red: 120/255, green: 190/255, blue: 140/255)
}
```

### Typography

- Body: `.body` (SF Pro)
- Caption: `.caption` / `.caption2`
- Monospace: `.system(.caption, design: .monospaced)` for hashes, session IDs, JSON
- Display: `.largeTitle.bold()` for screen headers

### Entity Shapes (DesignSystem/EntityShapes.swift)

Pure SwiftUI `Shape` implementations:
- `CowShape`: filled circle, radius proportional to canvas size
- `DroneShape`: equilateral triangle pointing in heading direction
- `PredatorShape`: X mark with threat ring
- Health ring: thin stroke circle overlay, color by health state

### Icons (SF Symbols)

| UI Element | SF Symbol |
|---|---|
| Live tab | `play.circle.fill` |
| Map tab | `map.fill` |
| Agents tab | `cpu.fill` |
| Alerts tab | `bell.badge.fill` |
| Ledger tab | `lock.shield.fill` |
| Active agent | `bolt.fill` |
| Idle agent | `moon.fill` |
| Scenario coyote | `pawprint.fill` |
| Scenario calving | `heart.fill` |
| Scenario storm | `cloud.bolt.fill` |
| Scenario water | `drop.fill` |
| Verify badge | `checkmark.seal.fill` |
| Breach pin | `exclamationmark.triangle.fill` |

### Sprites

No image sprites exist in `web/public/` — the web SPA draws everything in Canvas 2D. The iOS app should match this by using SwiftUI `Canvas` + `Shape` primitives. Do NOT attempt to fetch remote images for entity sprites.

---

## Testing Strategy

### Target Coverage
- 70%+ on `Networking/` + `Features/*/ViewModels/` (measured via Xcode coverage)
- UI views (`.swift` in `Features/*/` named `*View.swift`) are excluded from coverage requirement

### Unit Tests — XCTest

**ModelDecodeTests.swift**: Verify every `Codable` struct decodes correctly from fixture JSON.
```swift
func testWorldSnapshotDecode() throws {
    let data = try fixture("world_snapshot.json")
    let snapshot = try JSONDecoder().decode(WorldSnapshot.self, from: data)
    XCTAssertEqual(snapshot.cows.count, 12)
    XCTAssertFalse(snapshot.paddocks.isEmpty)
}
```

**SSEClientTests.swift**: Test the line parser (pure function, no network needed).
```swift
func testSSELineParsing() {
    let lines = ["event: world.snapshot", "data: {\"ts\":1.0}", ""]
    // Feed through parser → assert dispatches SkyHerdEvent.worldSnapshot
}

func testReconnectBackoffCalculation() {
    // Assert delay sequence: 1s, 2s, 4s, 8s, 16s, 30s (capped)
}
```

**LiveViewModelTests.swift**:
```swift
func testHandleScenarioActive() {
    let vm = LiveViewModel()
    vm.handle(ScenarioActiveEvent(name: "coyote", passIdx: 0, speed: 15, startedAt: "..."))
    XCTAssertEqual(vm.activeScenario, "coyote")
    XCTAssertEqual(vm.speed, 15.0)
}
```

**LedgerViewModelTests.swift**:
```swift
func testSearchFiltering() {
    let vm = LedgerViewModel()
    vm.entries = [/* fixtures */]
    vm.searchText = "cafebabe"
    XCTAssertTrue(vm.filteredEntries.allSatisfy { $0.eventHash.hasPrefix("cafebabe") })
}
```

### Test Fixtures

Capture real SSE payloads from the running backend:
```bash
# Start backend: make dashboard
# Capture events:
curl -N http://localhost:8000/events 2>&1 | head -100 > /tmp/sse_sample.txt
# Extract specific event types and save as JSON files in SkyHerdRancherTests/Fixtures/
```

Fixture files to create (one per model):
- `world_snapshot.json` — copy from mock output of `GET /api/snapshot`
- `cost_tick.json` — captured from SSE stream
- `attest_entry.json` — from `GET /api/attest`
- `agent_log.json` — from SSE agent.log event

---

## Build & Run

### Requirements

- Xcode 15.3+ (iOS 17 SDK)
- Simulator: iPhone 15 Pro (iOS 17+)
- No SPM dependencies (zero external packages — system frameworks only: SwiftUI, MapKit, Swift Charts, Foundation)
- Python backend must be running: `make dashboard` in repo root

### Xcode Project Setup

The implementation agent must create the Xcode project manually or via `xcodegen`. Recommended: create via Xcode UI (File → New → Project → iOS App), then add files. Target: `SkyHerdRancher`, Bundle ID: `com.skyherd.rancher`, Swift 5.9, iOS 17.0 minimum.

No `Package.swift` needed (no SPM deps). No CocoaPods.

### Make Target

Add to the root `Makefile`:
```makefile
ios-rancher-build:
	xcodebuild \
	  -project ios/SkyHerdRancher/SkyHerdRancher.xcodeproj \
	  -scheme SkyHerdRancher \
	  -destination 'platform=iOS Simulator,name=iPhone 15 Pro' \
	  build \
	  | xcpretty || true
```

### Demo Flow

1. Terminal A: `make dashboard` (starts backend + ambient driver)
2. Terminal B: open Xcode → `ios/SkyHerdRancher/SkyHerdRancher.xcodeproj` → Run on iPhone 15 Pro Simulator
3. App auto-connects to `localhost:8000`, shows live event feed
4. Scenario pills begin cycling; map shows moving cows
5. For recording: use screen recording on simulator while demo runs

### Simulator ↔ Localhost Note

iOS Simulator shares the Mac's network stack — `localhost:8000` resolves correctly. No ATS exceptions or `NSAppTransportSecurity` exceptions are needed for localhost `http://`. For a real device, add `NSAppTransportSecurity` exception for the server IP in `Info.plist`.

---

## Risks & Mitigations

### Risk 1: SSE Reconnection Noise
**Problem**: iOS URLSession drops SSE connection on app background, simulator sleep, or network hiccup. Backend returns 429 if reconnection storms hit the 100-connection limit.

**Mitigation**: Implement exponential backoff (1s → 2s → 4s → 8s → 16s → 30s cap) in `SSEClient`. Show "Reconnecting…" badge in UI during gap. Cancel ongoing task on `disconnect()` to avoid zombie connections counting against the cap.

### Risk 2: CORS for Real Device
**Problem**: If testing on a physical iPhone (not Simulator), the backend CORS allowlist only includes localhost origins. The iOS app's `http://192.168.x.x:8000` request will be CORS-blocked.

**Mitigation**: For hackathon demo, use Simulator only (localhost resolves correctly). If real device needed, set `SKYHERD_CORS_ORIGINS=http://localhost:8000,http://192.168.x.x:8000` before starting backend. Document in README.

### Risk 3: Decoding Evolution
**Problem**: Backend mock vs live mode produces different field sets (some fields present only in live mode). Strict `Decodable` will throw on missing required fields.

**Mitigation**: Make all non-primary fields optional (`?`) in Swift structs. Use `decodeIfPresent` semantics (Swift's default for `Optional` Codable properties). Confirm all structs follow this pattern in the backend map doc.

### Risk 4: Normalized Coordinates vs MapKit
**Problem**: World snapshot uses normalized `[0,1]` coords, not real GPS. MapKit requires `CLLocationCoordinate2D`. Mapping `[0,1]` → fake lat/lon accurately for MapPolygon paddock overlays requires careful bounding box math.

**Mitigation**: For the hackathon, use the SwiftUI `Canvas` approach (Option A) for the Map tab instead of MapKit. Canvas renders in 2D pixel space where `[0,1]` → `CGPoint` is trivial (`x * size.width`, `y * size.height`). This matches the web SPA exactly. MapKit is a stretch goal if time allows.

### Risk 5: Xcode Project File Setup Time
**Problem**: Creating an Xcode project, configuring targets, adding 30+ Swift files, and wiring the scheme is mechanical but slow. A mistake in project.pbxproj causes the `make ios-rancher-build` target to fail silently.

**Mitigation**: The implementation agent should create the Xcode project via Xcode UI first (File → New → Project), then add all Swift files as new files within Xcode. Never hand-edit `project.pbxproj`. Run a build in Xcode before trusting `make ios-rancher-build`. Use `xcpretty` to make build output legible.

### Risk 6: Swift Charts Availability
**Problem**: `import Charts` (Swift Charts) requires iOS 16+ and Xcode 14+. Deployment target must be exactly set.

**Mitigation**: Set deployment target to iOS 17.0 (already required for `@Observable`). Swift Charts is available. Import `Charts` in `AgentCardView.swift` only.

### Risk 7: `@MainActor` Isolation in AppState Routing
**Problem**: `SSEClient` runs on a background actor. Routing events to `@Observable` ViewModels must happen on `@MainActor` or property mutations will generate purple runtime warnings.

**Mitigation**: Mark the `route(_ event:)` method with `@MainActor`. The `Task { for await event in ... }` in `AppState.start()` will hop to main actor before calling `route`. Alternatively, annotate all ViewModel `handle()` methods with `@MainActor`.

---

## Implementation Phasing

### Wave A — Scaffold + Models + Networking (Parallel-safe, ~3h)

**Deliverable**: Xcode project builds cleanly, all models decode from fixtures, SSEClient parses lines, APIClient makes GET/POST calls. No UI yet.

Scope:
1. Create `ios/SkyHerdRancher/SkyHerdRancher.xcodeproj` via Xcode
2. Add all `Models/*.swift` files (copy structs from backend map doc verbatim)
3. Add `Networking/Configuration.swift`, `Networking/APIClient.swift`, `Networking/SSEClient.swift`
4. Add `App/AppState.swift` (routing stub, no ViewModels yet)
5. Add test target `SkyHerdRancherTests/`
6. Add fixture JSON files to test target
7. Write + pass `ModelDecodeTests` and `SSEClientTests`
8. Add `GET /api/scenarios` and `GET /api/status` to FastAPI backend (`src/skyherd/server/app.py`)
9. Verify: `make ios-rancher-build` succeeds

### Wave B — Live + Map Screens (~3h)

**Deliverable**: Tabs 1 and 2 functional. App shows live event feed and ranch map from running backend.

Scope:
1. Add `DesignSystem/Colors.swift`, `Typography.swift`, `EntityShapes.swift`
2. Add `SkyHerdRancherApp.swift` with `TabView` skeleton (5 empty tabs)
3. Implement `Features/Live/LiveViewModel.swift` + `LiveView.swift`
4. Implement `Features/Map/MapViewModel.swift` + `MapView.swift` (Canvas-based)
5. Wire AppState event routing for `world.snapshot`, `agent.log`, `cost.tick`, `scenario.active/ended`
6. Write + pass `LiveViewModelTests`
7. Manual test: run `make dashboard`, launch app, confirm live feed populates

### Wave C — Agents + Alerts + Ledger Screens (~3h)

**Deliverable**: All 5 tabs functional.

Scope:
1. Implement `Features/Agents/AgentsViewModel.swift` + `AgentsView.swift` + `AgentCardView.swift`
2. Implement `Features/Alerts/AlertsViewModel.swift` + `AlertsView.swift`
3. Implement `Features/Ledger/LedgerViewModel.swift` + `LedgerView.swift` + `LedgerDetailView.swift`
4. Wire remaining AppState routing
5. Write + pass `LedgerViewModelTests`
6. Manual test: verify all 5 tabs show correct data

### Wave D — Polish + Tests + Make Target (~2h)

**Deliverable**: Demo-ready. `make ios-rancher-build` clean. 70%+ coverage. README.

Scope:
1. Add `make ios-rancher-build` to root `Makefile`
2. Add tab badge count for Alerts tab
3. Add connection state indicator (toolbar badge: green dot = connected, red = disconnected)
4. Add Settings sheet (base URL input, clear for custom server IP)
5. Complete unit test coverage to 70%+
6. Write `ios/SkyHerdRancher/README.md` with demo instructions
7. End-to-end demo run: `make demo SEED=42 SCENARIO=all` + iOS app side-by-side

---

## Agent Prompt Starters (for each wave)

**Wave A agent**: "Implement Wave A of `docs/plans/2026-04-25-skyherd-rancher-ios-design.md`. Read both `docs/plans/` files before writing any code. Create the Xcode project and all Models/Networking layers. BEFORE implementing: (1) scan available skills, (2) use Context7 MCP — call resolve-library-id then query-docs — for SwiftUI iOS 17 Observable macro and URLSession AsyncBytes, (3) copy all Swift structs verbatim from the backend map doc. Do not implement library APIs from memory."

**Wave B agent**: "Implement Wave B of `docs/plans/2026-04-25-skyherd-rancher-ios-design.md`. Wave A is complete. Implement Live and Map tabs using SwiftUI Canvas (not MapKit) for the map. BEFORE implementing: (1) scan available skills, (2) use Context7 MCP for SwiftUI Canvas drawing API, (3) match the earthy dark color palette from `DesignSystem/Colors.swift` exactly. Do not invent new colors."

**Wave C agent**: "Implement Wave C of `docs/plans/2026-04-25-skyherd-rancher-ios-design.md`. Waves A and B are complete. Implement Agents, Alerts, and Ledger tabs. BEFORE implementing: (1) scan available skills, (2) use Context7 MCP for Swift Charts sparkline API, (3) use WebSearch to verify Swift Charts `LineMark` syntax for iOS 17. The Agents tab must show session IDs to prove real platform registration."

**Wave D agent**: "Implement Wave D of `docs/plans/2026-04-25-skyherd-rancher-ios-design.md`. Waves A–C are complete. Polish, complete test coverage to 70%+, add `make ios-rancher-build` target, write README. BEFORE implementing: (1) scan available skills, (2) verify `xcodebuild` command syntax with WebSearch, (3) run `make dashboard` and do a full end-to-end demo run before marking complete."
