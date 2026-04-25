import Foundation
import Observation

@Observable
@MainActor
final class AppState {
    // MARK: - Sub-components
    let apiClient: APIClient
    private let sseClient: SSEClient

    // MARK: - Per-screen ViewModels (created once, held here for the TabView)
    let liveVM: LiveViewModel
    let mapVM: MapViewModel
    let agentsVM: AgentsViewModel
    let alertsVM: AlertsViewModel
    let ledgerVM: LedgerViewModel

    // MARK: - Connection state (observable by views)
    var connectionState: SSEConnectionState = .disconnected
    var lastError: String? = nil

    // MARK: - Init

    init(baseURL: URL = Configuration.defaultBaseURL) {
        let client = APIClient(baseURL: baseURL)
        self.apiClient = client

        let sse = SSEClient(baseURL: baseURL, decoder: JSONDecoder())
        self.sseClient = sse

        let live = LiveViewModel(apiClient: client)
        self.liveVM = live
        self.mapVM = MapViewModel(apiClient: client)
        self.agentsVM = AgentsViewModel()
        self.alertsVM = AlertsViewModel()
        self.ledgerVM = LedgerViewModel()
    }

    // MARK: - Lifecycle

    func start() {
        // Wire SSE connection state back to AppState (SSEClient runs on its own actor)
        Task {
            await sseClient.setOnConnectionStateChange { [weak self] state in
                Task { @MainActor [weak self] in
                    self?.connectionState = state
                }
            }
        }

        // Start SSE event loop
        Task {
            let stream = await sseClient.events()
            for await event in stream {
                await route(event)
            }
        }

        // Initial REST fetches
        Task {
            await fetchInitialState()
        }
    }

    func stop() {
        Task {
            await sseClient.disconnect()
        }
    }

    // MARK: - Event routing

    private func route(_ event: SkyHerdEvent) async {
        await MainActor.run {
            switch event {
            case .worldSnapshot(let s):
                mapVM.handle(s)
            case .costTick(let t):
                agentsVM.handle(t)
                liveVM.handle(t)
            case .agentLog(let l):
                agentsVM.handle(l)
                liveVM.handle(l)
            case .attestAppend(let a):
                ledgerVM.handle(a)
            case .vetIntakeDrafted(let v):
                alertsVM.handle(v)
            case .neighborAlert(let n):
                alertsVM.handle(n)
                mapVM.handle(n)
            case .neighborHandoff(let h):
                alertsVM.handle(h)
            case .scenarioActive(let s):
                liveVM.handle(s)
                mapVM.handle(s)
            case .scenarioEnded(let s):
                liveVM.handle(s)
                mapVM.handle(s)
            case .memoryWritten(let m):
                agentsVM.handle(m)
            case .memoryRead(let m):
                agentsVM.handle(m)
            case .unknown:
                break
            }
        }
    }

    // MARK: - Initial state fetch

    private func fetchInitialState() async {
        // Fetch status for Live tab initial speed + scenario
        if let status = try? await apiClient.status() {
            await MainActor.run {
                liveVM.speed = status.speed
                liveVM.activeScenario = status.activeScenario
            }
        }

        // Fetch world snapshot for Map tab
        if let snapshot = try? await apiClient.snapshot() {
            await MainActor.run {
                mapVM.handle(snapshot)
            }
        }

        // Fetch agent statuses
        if let agentResp = try? await apiClient.agents() {
            await MainActor.run {
                agentsVM.handleInitial(agentResp.agents)
            }
        }

        // Fetch initial attestation ledger
        if let attestResp = try? await apiClient.attestations(sinceSeq: 0) {
            await MainActor.run {
                ledgerVM.handleInitial(attestResp.entries)
            }
        }
    }
}

// MARK: - SSEClient connection state callback helper
extension SSEClient {
    func setOnConnectionStateChange(_ handler: @escaping (SSEConnectionState) -> Void) {
        onConnectionStateChange = handler
    }
}
