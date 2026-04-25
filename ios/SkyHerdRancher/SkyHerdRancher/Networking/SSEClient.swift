import Foundation

// MARK: - Connection state

enum SSEConnectionState: Equatable {
    case disconnected
    case connecting
    case connected
    case reconnecting(attempt: Int)
    case failed(String)

    var description: String {
        switch self {
        case .disconnected:          return "Disconnected"
        case .connecting:            return "Connecting…"
        case .connected:             return "Connected"
        case .reconnecting(let n):   return "Reconnecting… (attempt \(n))"
        case .failed(let msg):       return "Failed: \(msg)"
        }
    }
}

// MARK: - SSEClient actor

actor SSEClient {
    private let url: URL
    private let decoder: JSONDecoder
    private var currentTask: Task<Void, Never>?

    // Backoff: 1s, 2s, 4s, 8s, 16s, 30s (cap)
    private static let backoffDelays: [Double] = [1, 2, 4, 8, 16, 30]

    // Published connection state — main-actor consumers should observe via AppState
    private var _connectionState: SSEConnectionState = .disconnected
    var connectionState: SSEConnectionState { _connectionState }

    // State change callback so AppState can forward to @Observable without Combine
    var onConnectionStateChange: ((SSEConnectionState) -> Void)?

    init(baseURL: URL, decoder: JSONDecoder = JSONDecoder()) {
        self.url = URL(string: "/events", relativeTo: baseURL)!
        self.decoder = decoder
    }

    // MARK: - Public API

    /// Returns an AsyncStream of decoded events. Starts the SSE connection.
    /// The stream never completes — call disconnect() to cancel.
    func events() -> AsyncStream<SkyHerdEvent> {
        AsyncStream { continuation in
            self.currentTask?.cancel()
            self.currentTask = Task {
                await self.runLoop(continuation: continuation)
            }
        }
    }

    func disconnect() {
        currentTask?.cancel()
        currentTask = nil
        updateState(.disconnected)
    }

    // MARK: - Internal loop

    private func runLoop(continuation: AsyncStream<SkyHerdEvent>.Continuation) async {
        var attempt = 0

        while !Task.isCancelled {
            updateState(attempt == 0 ? .connecting : .reconnecting(attempt: attempt))

            do {
                try await connectOnce(continuation: continuation)
                // If we get here the stream ended without error — reconnect
                attempt = 0
            } catch is CancellationError {
                break
            } catch {
                attempt += 1
                let delay = SSEClient.backoffDelay(attempt: attempt)
                updateState(.reconnecting(attempt: attempt))
                try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            }
        }

        updateState(.disconnected)
        continuation.finish()
    }

    private func connectOnce(continuation: AsyncStream<SkyHerdEvent>.Continuation) async throws {
        var request = URLRequest(url: url)
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        request.setValue("no-cache", forHTTPHeaderField: "Cache-Control")
        request.timeoutInterval = .infinity

        let (asyncBytes, response) = try await URLSession.shared.bytes(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              (200..<300).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }

        updateState(.connected)

        var frame = SSEFrame()

        for try await line in asyncBytes.lines {
            if Task.isCancelled { break }

            if line.hasPrefix("event:") {
                frame.eventType = String(line.dropFirst(6)).trimmingCharacters(in: .whitespaces)
            } else if line.hasPrefix("data:") {
                let chunk = String(line.dropFirst(5)).trimmingCharacters(in: .whitespaces)
                if frame.data.isEmpty {
                    frame.data = chunk
                } else {
                    frame.data += "\n" + chunk
                }
            } else if line.hasPrefix(":") {
                // SSE comment / keep-alive — ignore
            } else if line.isEmpty {
                // Blank line = end of frame
                if !frame.data.isEmpty,
                   let event = SkyHerdEvent.decode(frame: frame, decoder: decoder) {
                    continuation.yield(event)
                }
                frame = SSEFrame()
            }
        }
    }

    private func updateState(_ state: SSEConnectionState) {
        _connectionState = state
        onConnectionStateChange?(state)
    }

    // MARK: - Backoff calculation

    static func backoffDelay(attempt: Int) -> Double {
        let idx = min(attempt - 1, backoffDelays.count - 1)
        let base = backoffDelays[max(0, idx)]
        // Add up to 500ms jitter to avoid thundering herd
        let jitter = Double.random(in: 0..<0.5)
        return base + jitter
    }
}
