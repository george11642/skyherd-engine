import Foundation
import Combine

/// Observable application state shared between UI and service layers.
@MainActor
public final class AppState: ObservableObject {
    // MARK: Connection status strings (UI display)
    @Published public var djiStatus: String = "Not registered"
    @Published public var wsStatus: String = "Stopped"
    @Published public var mqttStatus: String = "Disconnected"

    // MARK: Last command info
    @Published public var lastCmdId: String = "--"
    @Published public var lastCmdTs: Date? = nil

    // MARK: Drone snapshot
    @Published public var droneState: DroneStateSnapshot = DroneStateSnapshot()

    // MARK: Error display
    @Published public var lastError: String? = nil

    public init() {}

    /// Update last-command display (called from CommandRouter on each dispatch).
    public func recordCommand(id: String) {
        lastCmdId = id
        lastCmdTs = Date()
    }
}
