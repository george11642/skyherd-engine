import Foundation

enum Configuration {
    static let baseURLDefaultsKey = "skyherd_base_url"
    static let baseURLLaunchArgKey = "-SkyHerdBaseURL"

    static var defaultBaseURL: URL {
        // 1. Launch argument: -SkyHerdBaseURL http://192.168.1.5:8000
        let args = ProcessInfo.processInfo.arguments
        if let idx = args.firstIndex(of: baseURLLaunchArgKey),
           idx + 1 < args.count,
           let url = URL(string: args[idx + 1]) {
            return url
        }

        // 2. UserDefaults override (from Settings sheet)
        if let stored = UserDefaults.standard.string(forKey: baseURLDefaultsKey),
           let url = URL(string: stored) {
            return url
        }

        // 3. Default: localhost:8000
        return URL(string: "http://localhost:8000")!
    }
}
