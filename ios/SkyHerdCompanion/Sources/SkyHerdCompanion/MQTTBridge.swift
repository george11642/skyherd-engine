import Foundation
import CocoaMQTT
#if canImport(UIKit)
import UIKit
#endif

// MARK: - MQTTBridge

/// Maintains an MQTT connection to the ranch broker and:
///
/// - Subscribes to ``skyherd/drone/cmd/#`` to receive commands from the
///   SkyHerd Engine laptop.
/// - Publishes state snapshots on ``skyherd/drone/state/ios``.
/// - Publishes ACKs on ``skyherd/drone/ack/ios``.
///
/// Topic scheme follows ``docs/MAVIC_MISSION_SCHEMA.md`` §5 — the base
/// (`skyherd/drone`) is shared with Android; the `/ios` suffix identifies
/// the sending platform to the backend.
///
/// Auto-reconnects with exponential back-off (1 s → 128 s max).
@MainActor
public final class MQTTBridge: NSObject {
    public static let shared = MQTTBridge()

    // MARK: - State
    public private(set) var isConnected = false

    // MARK: - Dependencies
    private var router: CommandRouter?
    private var appState: AppState?

    // MARK: - MQTT client
    private var mqtt: CocoaMQTT?

    // MARK: - Topic constants
    private var topicBase: String { Config.mqttTopicBase }
    private var cmdTopic: String { "\(topicBase)/cmd/#" }
    private var stateTopic: String { "\(topicBase)/state/ios" }
    private var ackTopic: String { "\(topicBase)/ack/ios" }
    private var statusTopic: String { "\(topicBase)/status/ios" }

    private override init() {
        super.init()
    }

    // MARK: - Connect

    /// Wire up dependencies and connect to the broker.
    public func start(router: CommandRouter, appState: AppState) {
        self.router = router
        self.appState = appState
        connect()
    }

    private func connect() {
        let clientID = "SkyHerdCompanion-iOS-\(deviceIdentifier())"
        let client = CocoaMQTT(clientID: clientID, host: Config.mqttHost, port: Config.mqttPort)
        client.keepAlive = 60
        client.cleanSession = true
        client.autoReconnect = true
        client.autoReconnectTimeInterval = 1
        client.maxAutoReconnectTimeInterval = 128
        client.logLevel = .warning
        client.willMessage = CocoaMQTTMessage(
            topic: statusTopic,
            string: "offline",
            qos: .qos1,
            retained: true
        )
        client.delegate = self
        mqtt = client
        _ = client.connect()
        AppLogger.mqtt.info("MQTT connecting to \(Config.mqttHost):\(Config.mqttPort)")
    }

    // MARK: - Publish

    /// Publish a drone state snapshot.
    public func publishState(_ state: DroneStateSnapshot) {
        guard isConnected, let mqtt else { return }
        let payload = MQTTStatePayload(state: state)
        guard let data = try? JSONEncoder().encode(payload),
              let json = String(data: data, encoding: .utf8)
        else { return }
        mqtt.publish(stateTopic, withString: json, qos: .qos0, retained: true)
    }

    /// Publish an ACK.
    public func publishAck(_ ack: DroneAck) {
        guard isConnected, let mqtt else { return }
        let payload = MQTTAckPayload(ack: ack)
        guard let data = try? JSONEncoder().encode(payload),
              let json = String(data: data, encoding: .utf8)
        else { return }
        mqtt.publish(ackTopic, withString: json, qos: .qos1, retained: false)
    }

    // MARK: - Helpers

    private func deviceIdentifier() -> String {
        #if canImport(UIKit)
        return UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString
        #else
        // Non-UIKit contexts (macOS unit tests) — return a stable fallback.
        return UUID().uuidString
        #endif
    }

    /// Expose the decoded command pipeline to unit tests. Decodes the payload
    /// and routes through the injected router, returning the resulting ACK.
    @discardableResult
    public func _decodeAndDispatch(payload: Data) async -> DroneAck? {
        guard let router = router else { return nil }
        do {
            let cmd = try JSONDecoder().decode(DroneCommand.self, from: payload)
            return await router.dispatch(cmd)
        } catch {
            AppLogger.mqtt.error("_decodeAndDispatch: decode failed \(error)")
            return nil
        }
    }

    private func handleIncomingMessage(_ message: CocoaMQTTMessage) {
        guard let json = message.string?.data(using: .utf8) else { return }
        do {
            let cmd = try JSONDecoder().decode(DroneCommand.self, from: json)
            AppLogger.mqtt.info("MQTT cmd received: \(cmd.cmd) seq=\(cmd.seq)")
            Task { @MainActor [weak self] in
                guard let self, let router = self.router else { return }
                let ack = await router.dispatch(cmd)
                self.publishAck(ack)
            }
        } catch {
            AppLogger.mqtt.error("MQTT: failed to decode command: \(error)")
        }
    }
}

// MARK: - CocoaMQTTDelegate

extension MQTTBridge: CocoaMQTTDelegate {
    public nonisolated func mqtt(_ mqtt: CocoaMQTT, didConnectAck ack: CocoaMQTTConnAck) {
        Task { @MainActor in
            if ack == .accept {
                self.isConnected = true
                self.appState?.mqttStatus = "Connected"
                AppLogger.mqtt.info("MQTT connected")
                // Subscribe to command topic
                mqtt.subscribe(self.cmdTopic, qos: .qos1)
                // Publish online status
                mqtt.publish(
                    self.statusTopic,
                    withString: "online",
                    qos: .qos1,
                    retained: true
                )
            } else {
                AppLogger.mqtt.error("MQTT connect rejected: \(ack.rawValue)")
                self.appState?.mqttStatus = "Rejected (\(ack.rawValue))"
            }
        }
    }

    public nonisolated func mqttDidDisconnect(_ mqtt: CocoaMQTT, withError err: Error?) {
        Task { @MainActor in
            self.isConnected = false
            let reason = err?.localizedDescription ?? "clean"
            AppLogger.mqtt.warning("MQTT disconnected: \(reason)")
            self.appState?.mqttStatus = "Disconnected"
        }
    }

    public nonisolated func mqtt(_ mqtt: CocoaMQTT, didReceiveMessage message: CocoaMQTTMessage, id: UInt16) {
        Task { @MainActor in
            self.handleIncomingMessage(message)
        }
    }

    public nonisolated func mqtt(_ mqtt: CocoaMQTT, didSubscribeTopics success: NSDictionary, failed: [String]) {
        AppLogger.mqtt.info("MQTT subscribed to command topic")
    }

    public nonisolated func mqtt(_ mqtt: CocoaMQTT, didPublishMessage message: CocoaMQTTMessage, id: UInt16) {}
    public nonisolated func mqtt(_ mqtt: CocoaMQTT, didPublishAck id: UInt16) {}
    public nonisolated func mqtt(_ mqtt: CocoaMQTT, didUnsubscribeTopics topics: [String]) {}
    public nonisolated func mqttDidPing(_ mqtt: CocoaMQTT) {}
    public nonisolated func mqttDidReceivePong(_ mqtt: CocoaMQTT) {}
}
