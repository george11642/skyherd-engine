import Foundation

actor APIClient {
    let baseURL: URL
    private let session: URLSession
    let decoder: JSONDecoder

    init(baseURL: URL = Configuration.defaultBaseURL) {
        self.baseURL = baseURL
        self.session = URLSession.shared
        self.decoder = JSONDecoder()
        // All date fields are Double epoch seconds or ISO strings — no decoder date strategy needed
    }

    // MARK: - Generic helpers

    func get<T: Decodable>(_ path: String) async throws -> T {
        let request = try buildRequest(path: path, method: "GET")
        return try await execute(request)
    }

    func post<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        var request = try buildRequest(path: path, method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)
        return try await execute(request)
    }

    func postEmpty(_ path: String) async throws -> Data {
        var request = try buildRequest(path: path, method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return data
    }

    // MARK: - Named endpoint methods

    func health() async throws -> HealthResponse {
        try await get("/health")
    }

    func snapshot() async throws -> WorldSnapshot {
        try await get("/api/snapshot")
    }

    func agents() async throws -> AgentsResponse {
        try await get("/api/agents")
    }

    func scenarios() async throws -> ScenariosResponse {
        try await get("/api/scenarios")
    }

    func status() async throws -> StatusResponse {
        try await get("/api/status")
    }

    func attestations(sinceSeq: Int = 0) async throws -> AttestResponse {
        try await get("/api/attest?since_seq=\(sinceSeq)")
    }

    func verifyAttestation() async throws -> VerifyResult {
        let data = try await postEmpty("/api/attest/verify")
        return try decoder.decode(VerifyResult.self, from: data)
    }

    func attestByHash(_ hash: String) async throws -> AttestByHashResponse {
        try await get("/api/attest/by-hash/\(hash)")
    }

    func attestPair(_ memverId: String) async throws -> AttestPairResponse {
        try await get("/api/attest/pair/\(memverId)")
    }

    func memory(agent: String, pathPrefix: String? = nil) async throws -> MemoryResponse {
        var path = "/api/memory/\(agent)"
        if let prefix = pathPrefix {
            path += "?path_prefix=\(prefix)"
        }
        return try await get(path)
    }

    func neighbors() async throws -> NeighborsResponse {
        try await get("/api/neighbors")
    }

    func vetIntake(id: String) async throws -> String {
        let request = try buildRequest(path: "/api/vet-intake/\(id)", method: "GET")
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return String(data: data, encoding: .utf8) ?? ""
    }

    func setSpeed(_ speed: Double) async throws -> SpeedResponse {
        struct Body: Encodable { let speed: Double }
        do {
            return try await post("/api/ambient/speed", body: Body(speed: speed))
        } catch APIError.httpError(let code, _) where code == 404 {
            throw APIError.notAttached
        }
    }

    func skipScenario() async throws -> SkipResponse {
        do {
            let data = try await postEmpty("/api/ambient/next")
            return try decoder.decode(SkipResponse.self, from: data)
        } catch APIError.httpError(let code, _) where code == 404 {
            throw APIError.notAttached
        }
    }

    // MARK: - Private helpers

    private func buildRequest(path: String, method: String) throws -> URLRequest {
        guard let url = URL(string: path, relativeTo: baseURL) else {
            throw APIError.invalidURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        return request
    }

    private func execute<T: Decodable>(_ request: URLRequest) async throws -> T {
        do {
            let (data, response) = try await session.data(for: request)
            try validate(response: response, data: data)
            do {
                return try decoder.decode(T.self, from: data)
            } catch {
                throw APIError.decodingError(error)
            }
        } catch let e as APIError {
            throw e
        } catch {
            throw APIError.networkError(error)
        }
    }

    private func validate(response: URLResponse, data: Data) throws {
        guard let httpResponse = response as? HTTPURLResponse else { return }
        let code = httpResponse.statusCode
        guard (200..<300).contains(code) else {
            let detail = String(data: data, encoding: .utf8)
            throw APIError.httpError(statusCode: code, detail: detail)
        }
    }
}
