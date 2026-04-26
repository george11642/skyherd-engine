import SwiftUI

// MARK: - SkyHerd color palette
// Sourced from web/src/index.css CSS custom properties

extension Color {
    // Backgrounds
    static let skhBg0   = Color(red: 10/255,  green: 12/255,  blue: 16/255)   // Deep background
    static let skhBg1   = Color(red: 16/255,  green: 19/255,  blue: 25/255)   // Card background
    static let skhBg2   = Color(red: 24/255,  green: 28/255,  blue: 36/255)   // Elevated surface
    static let skhLine  = Color(red: 38/255,  green: 45/255,  blue: 58/255)   // Divider / border

    // Text
    static let skhText0 = Color(red: 236/255, green: 239/255, blue: 244/255)  // Primary text
    static let skhText1 = Color(red: 168/255, green: 180/255, blue: 198/255)  // Secondary text
    static let skhText2 = Color(red: 110/255, green: 122/255, blue: 140/255)  // Tertiary / placeholder

    // Accents
    static let skhSage    = Color(red: 148/255, green: 176/255, blue: 136/255) // Healthy cow, forage
    static let skhDust    = Color(red: 210/255, green: 178/255, blue: 138/255) // Watch / caution / earthy
    static let skhThermal = Color(red: 255/255, green: 143/255, blue: 60/255)  // Thermal / active agent
    static let skhSky     = Color(red: 120/255, green: 180/255, blue: 220/255) // Drone / sky blue
    static let skhWarn    = Color(red: 240/255, green: 195/255, blue: 80/255)  // Warning / amber
    static let skhDanger  = Color(red: 224/255, green: 100/255, blue: 90/255)  // Sick / predator / threat
    static let skhOk      = Color(red: 120/255, green: 190/255, blue: 140/255) // Verified / safe

    // Entity colors (matching web SPA RanchMap.tsx)
    static let skhCowHealthy  = skhSage          // #94b088
    static let skhCowWatch    = skhDust          // #d2b28a
    static let skhCowSick     = skhDanger        // #e0645a
    static let skhCowCalving  = skhSky           // #78b4dc
    static let skhDroneColor  = skhSky           // #78b4dc
    static let skhPredator    = skhDanger        // #e0645a
}
