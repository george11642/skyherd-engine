import Foundation
import Observation
import UIKit

@Observable
@MainActor
final class LiveViewModel {

    // MARK: - State

    var activeScenario: String? = nil
    var speed: Double = 15.0
    var isPaused: Bool = false
    var recentEvents: [AgentLogEvent] = []   // capped at 50, newest first
    var costRate: Double = 0.0
    var allIdle: Bool = true
    var scenarios: [String] = []             // populated on appear
    var toastMessage: String? = nil          // transient error toast
    var isLoadingScenarios: Bool = false

    private let maxEvents = 50
    var apiClient: APIClient?

    // Speed debounce
    private var speedDebounceTask: Task<Void, Never>?

    // MARK: - Init

    init(apiClient: APIClient? = nil) {
        self.apiClient = apiClient
    }

    // MARK: - Event handlers (called by AppState.route)

    func handle(_ event: AgentLogEvent) {
        recentEvents.insert(event, at: 0)
        if recentEvents.count > maxEvents {
            recentEvents.removeLast()
        }
    }

    func handle(_ tick: CostTick) {
        costRate = tick.ratePerHrUsd
        allIdle = tick.allIdle
    }

    func handle(_ event: ScenarioActiveEvent) {
        activeScenario = event.name
        speed = event.speed
    }

    func handle(_ event: ScenarioEndedEvent) {
        activeScenario = nil
    }

    // MARK: - Actions

    func loadScenarios() async {
        guard let apiClient else { return }
        isLoadingScenarios = true
        defer { isLoadingScenarios = false }
        do {
            let resp = try await apiClient.scenarios()
            scenarios = resp.scenarios
        } catch {
            // Fall back to hard-coded list if endpoint not yet live
            scenarios = [
                "coyote", "sick_cow", "water_drop", "calving",
                "storm", "wildfire", "rustling", "cross_ranch_coyote"
            ]
        }
    }

    func skipToNextScenario() async {
        guard let apiClient else { return }
        let feedback = UIImpactFeedbackGenerator(style: .medium)
        feedback.impactOccurred()
        do {
            _ = try await apiClient.skipScenario()
        } catch APIError.notAttached {
            showToast("Speed control requires live mode (make dashboard)")
        } catch {
            showToast("Failed to skip scenario: \(error.localizedDescription)")
        }
    }

    func togglePlayback() {
        isPaused.toggle()
        let feedback = UIImpactFeedbackGenerator(style: .medium)
        feedback.impactOccurred()
    }

    /// Called on slider release (debounced 300ms).
    func setSpeed(_ newSpeed: Double) {
        speed = newSpeed
        speedDebounceTask?.cancel()
        speedDebounceTask = Task {
            try? await Task.sleep(nanoseconds: 300_000_000)
            guard !Task.isCancelled else { return }
            await sendSpeedToBackend(newSpeed)
        }
    }

    private func sendSpeedToBackend(_ value: Double) async {
        guard let apiClient else { return }
        do {
            _ = try await apiClient.setSpeed(value)
        } catch APIError.notAttached {
            showToast("Speed control requires live mode")
        } catch {
            // Silent — speed updates fail gracefully in mock mode
        }
    }

    private func showToast(_ message: String) {
        toastMessage = message
        Task {
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            if toastMessage == message {
                toastMessage = nil
            }
        }
    }

    // MARK: - Logarithmic speed helpers

    /// Convert slider position [0,1] → speed value [1, 100] using log scale
    static func sliderToSpeed(_ t: Double) -> Double {
        let clamped = max(0, min(1, t))
        let logMin = log10(1.0)
        let logMax = log10(100.0)
        return pow(10.0, logMin + clamped * (logMax - logMin))
    }

    /// Convert speed value [1, 100] → slider position [0, 1]
    static func speedToSlider(_ speed: Double) -> Double {
        let clamped = max(1.0, min(100.0, speed))
        let logMin = log10(1.0)
        let logMax = log10(100.0)
        return (log10(clamped) - logMin) / (logMax - logMin)
    }
}
