# SkyHerdRancher — iOS App

Native SwiftUI companion app for the SkyHerd ranch simulation. Built for the Anthropic "Built with Opus 4.7" hackathon.

## Overview

SkyHerdRancher is a live-viewer iOS app that connects to the SkyHerd FastAPI backend (`localhost:8000`) via REST + SSE. It shows the 5-agent AI mesh in real time — live event feed, animated ranch map, agent stats, alerts, and the Ed25519 attestation ledger. Judges can hold a phone (or simulator) next to the laptop demo to see the same simulation play out natively.

## Quickstart

```bash
# 1. Start the backend
make dashboard

# 2. Build + launch in iPhone 15 Pro Simulator
make ios-rancher-run

# 3. Or do both in one command (waits 30s for backend)
make ios-rancher-demo
```

Requirements: Xcode 15.3+, macOS 14+. No SPM dependencies — zero external packages.

## Screenshots

| Live | Map | Agents | Alerts | Ledger |
|------|-----|--------|--------|--------|
| ![Live](screenshots/live.png) | ![Map](screenshots/map.png) | ![Agents](screenshots/agents.png) | ![Alerts](screenshots/alerts.png) | ![Ledger](screenshots/ledger.png) |

## Architecture

SwiftUI iOS 17+ · MVVM with `@Observable` macro (no `ObservableObject`) · REST + SSE to FastAPI at `:8000`.

- **`AppState`** — `@Observable @MainActor` class, owns `SSEClient` and all 5 ViewModels. Created once at app entry, passed down via `.environment(appState)`.
- **`SSEClient`** — actor-isolated `URLSession AsyncBytes` reader with exponential-backoff reconnect (1s → 2s → 4s → 8s → 16s → 30s cap).
- **`APIClient`** — actor-isolated REST client with typed endpoints: `GET /api/status`, `GET /api/scenarios`, `GET /api/snapshot`, `GET /api/agents`, `GET /api/attest`, `POST /api/ambient/speed`, `POST /api/ambient/next`.
- **ViewModels** — one per tab, plain `@Observable` classes wired to AppState via event routing. No Combine, no `@Published`. Swift Concurrency throughout.
- **Map tab** — SwiftUI `Canvas` (not MapKit). Normalized `[0,1]` coords map directly to `CGPoint` in 2D canvas space, matching the web SPA exactly.

## Configuration

### Changing the backend URL

Three ways (in priority order):

1. **Launch argument** (for `xcodebuild -destination`):
   ```
   -SkyHerdBaseURL http://192.168.1.5:8000
   ```

2. **UserDefaults** — long-press the "Live" / "Offline" connection badge in the app to open the Debug Info sheet. Edit the URL and tap Save. Restart the app to apply.

3. **Default** — `http://localhost:8000` (iOS Simulator shares the Mac's network stack; localhost works out of the box).

### ATS (App Transport Security)

`NSAllowsLocalNetworking = YES` is set in `Info.plist`. No ATS exceptions are needed for `localhost` HTTP. For a real device pointing at a LAN IP, add the server's IP to the `NSExceptionDomains` in `Info.plist` or use HTTPS.

## Make Targets

| Target | Description |
|--------|-------------|
| `make ios-rancher-build` | Fast build (generic iOS Simulator destination) |
| `make ios-rancher-test` | Run 86 unit tests on iPhone 15 Pro Simulator |
| `make ios-rancher-run` | Build + install + launch on iPhone 15 Pro Simulator |
| `make ios-rancher-demo` | Start backend + launch app (full demo flow) |

## Troubleshooting

**"Connection: Offline" badge** — Backend is not running. Run `make dashboard` in the repo root.

**CORS errors on real device** — The iOS Simulator uses the Mac's localhost. A physical iPhone needs the server IP and a CORS exception. Set `SKYHERD_CORS_ORIGINS=http://192.168.x.x:8000` before starting the backend.

**SourceKit phantom "missing file" errors** — Xcode's SourceKit index can drift. Ignore these if `make ios-rancher-build` is green — only `xcodebuild` results matter for CI. To reset: Product → Clean Build Folder, then rebuild.

**Simulator not found** — Run `xcrun simctl list devices available | grep "iPhone 15 Pro"` to confirm the simulator exists. If missing, create it in Xcode → Devices & Simulators.

**`make ios-rancher-demo` backend timeout** — `make dashboard` downloads npm packages on first run. Run `make dashboard` once manually and wait for it to start, then use `make ios-rancher-run` directly.

## Design Docs

- Architecture: `docs/plans/2026-04-25-skyherd-rancher-ios-design.md`
- Backend API map: `docs/plans/2026-04-25-ios-backend-map.md`
- Project overview: `docs/ONE_PAGER.md`
