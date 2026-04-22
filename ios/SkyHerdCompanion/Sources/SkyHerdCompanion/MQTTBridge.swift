import Foundation
import CocoaMQTT

// MARK: - MQTTBridge

/// Maintains an MQTT connection to the ranch broker and:
/// - Subscribes to ``skyherd/drone/cmd/#`` to receive commands as an alternative
///   transport to WebSocket (useful when phone is on WiFi with direct broker access).
/// - Publishes state snapshots on ``skyherd/drone/state/ios``.
/// - Publishes ACKs on ``skyherd/drone/ack/ios``.
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
        let clientID = "SkyHerdCompanion-iOS-\(UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString)"
        let client = CocoaMQTT(clientID: clientID, host: Config.mqttHost, port: Config.mqttPort)
        client.keepAlive = 60
        client.cleanSession = true
        client.autoReconnect = true
        client.autoReconnectTimeInterval = 1
        client.maxAutoReconnectTimeInterval = 128
        client.logLevel = .warning
        client.willMessage = CocoaMQTTMessage(
            topic: "\(topicBase)/status/ios",
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
                    "\(self.topicBase)/status/ios",
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

// MARK: - UIDevice import shim (available in UIKit contexts only)
#if canImport(UIKit)
import UIKit
#else
// SwiftUI Previews / unit tests on simulator without full UIKit
private enum UIDevice {
    static var current: UIDeviceStub { UIDeviceStub() }
    struct UIDeviceStub {
        var identifierForVendor: UUID? { UUID(uuidString: "00000000-0000-0000-0000-000000000000") }
    }
}
#endif
