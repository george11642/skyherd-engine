import Foundation

struct WorldSnapshot: Codable {
    let ts: Double
    let simTimeS: Double
    let clockIso: String
    let isNight: Bool
    let weather: Weather
    let cows: [Cow]
    let predators: [Predator]
    let drone: Drone
    let paddocks: [Paddock]
    let waterTanks: [WaterTank]

    enum CodingKeys: String, CodingKey {
        case ts, cows, predators, drone, paddocks, weather
        case simTimeS = "sim_time_s"
        case clockIso = "clock_iso"
        case isNight = "is_night"
        case waterTanks = "water_tanks"
    }
}

struct Weather: Codable {
    let conditions: String   // "clear" | "cloudy" | "storm"
    let tempF: Double
    let windKt: Double
    let humidityPct: Double

    enum CodingKeys: String, CodingKey {
        case conditions
        case tempF = "temp_f"
        case windKt = "wind_kt"
        case humidityPct = "humidity_pct"
    }
}

struct Cow: Codable, Identifiable {
    let id: String
    let tag: String?
    let pos: [Double]         // [x, y] normalized 0.0–1.0
    let bcs: Double?          // body condition score 1–9
    let state: String?        // "grazing"|"resting"|"walking"|"sick"|"calving"|"labor"
    let headingDeg: Double?

    enum CodingKeys: String, CodingKey {
        case id, tag, pos, bcs, state
        case headingDeg = "heading_deg"
    }
}

struct Predator: Codable, Identifiable {
    let id: String
    let pos: [Double]         // [x, y] normalized
    let species: String?      // "coyote"
    let threatLevel: String?  // "low"|"medium"|"high"

    enum CodingKeys: String, CodingKey {
        case id, pos, species
        case threatLevel = "threat_level"
    }
}

struct Drone: Codable {
    let lat: Double?
    let lon: Double?
    let altM: Double?
    let state: String?        // "idle"|"patrol"|"investigating"
    let batteryPct: Double?

    enum CodingKeys: String, CodingKey {
        case lat, lon, state
        case altM = "alt_m"
        case batteryPct = "battery_pct"
    }
}

struct Paddock: Codable, Identifiable {
    let id: String
    let bounds: [Double]      // [minX, minY, maxX, maxY] normalized
    let foragePct: Double

    enum CodingKeys: String, CodingKey {
        case id, bounds
        case foragePct = "forage_pct"
    }
}

struct WaterTank: Codable, Identifiable {
    let id: String
    let pos: [Double]         // [x, y] normalized
    let levelPct: Double

    enum CodingKeys: String, CodingKey {
        case id, pos
        case levelPct = "level_pct"
    }
}
