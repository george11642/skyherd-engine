import Foundation

enum APIError: Error, LocalizedError {
    case httpError(statusCode: Int, detail: String?)
    case decodingError(Error)
    case networkError(Error)
    case invalidURL
    case notAttached   // 404 from /api/ambient/* when driver not running

    var errorDescription: String? {
        switch self {
        case .httpError(let code, let detail):
            if let d = detail { return "Server error \(code): \(d)" }
            return "Server error \(code)"
        case .decodingError(let err):
            return "Decode error: \(err.localizedDescription)"
        case .networkError(let err):
            return "Network error: \(err.localizedDescription)"
        case .invalidURL:
            return "Invalid URL"
        case .notAttached:
            return "Live driver not attached — start the backend with `make dashboard`"
        }
    }
}
