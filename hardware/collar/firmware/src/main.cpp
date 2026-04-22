/**
 * SkyHerd DIY LoRa GPS Cattle Collar — Firmware
 * Target: RAK3172 (STM32WL53 + SX1262) running RAK RUI3
 *
 * Behaviour (every SEND_INTERVAL_MIN minutes):
 *   1. Wake from deep sleep
 *   2. Power-on GPS, wait for fix (timeout GPS_FIX_TIMEOUT_S seconds)
 *   3. Read MPU-6050, compute 10s rolling activity score
 *   4. Sample battery ADC
 *   5. Encode 16-byte payload (see CollarPayload struct)
 *   6. LoRaWAN uplink, port 2, unconfirmed
 *   7. Handle downlinks (port 1 = set interval, port 99 = reboot)
 *   8. Deep sleep until next cycle
 *
 * Payload layout (little-endian, 16 bytes):
 *   [0..3]  int32  lat_e7         latitude  x 1e7 (e.g. 340523401)
 *   [4..7]  int32  lon_e7         longitude x 1e7 (e.g. -1065342812)
 *   [8..9]  int16  alt_m          altitude in whole metres
 *   [10]    uint8  activity_code  0=resting 1=grazing 2=walking
 *   [11]    uint8  battery_pct    0-100
 *   [12..13]uint16 fix_age_s      age of GPS fix in seconds (0 = fresh)
 *   [14..15]uint16 uptime_s       seconds since last reboot (wraps at 65535)
 */

#include <Arduino.h>
#include <Wire.h>

// ---- project headers -------------------------------------------------------
#include "secrets.h"    // DEV_EUI / APP_EUI / APP_KEY (gitignored)

// ---- third-party -----------------------------------------------------------
#include <TinyGPS++.h>
#include <MPU6050.h>

// ---- compile-time configuration (can be overridden in platformio.ini) ------
#ifndef SEND_INTERVAL_MIN
  #define SEND_INTERVAL_MIN     15
#endif
#ifndef GPS_FIX_TIMEOUT_S
  #define GPS_FIX_TIMEOUT_S     90
#endif
#ifndef GPS_UART_BAUD
  #define GPS_UART_BAUD         9600
#endif
#ifndef GPS_UART_FAST_BAUD
  #define GPS_UART_FAST_BAUD    115200
#endif
#ifndef IMU_ACTIVITY_WINDOW_S
  #define IMU_ACTIVITY_WINDOW_S 10
#endif
#ifndef LOW_BATTERY_THRESHOLD_PCT
  #define LOW_BATTERY_THRESHOLD_PCT 15
#endif

// ---- ADC voltage divider constants -----------------------------------------
// LiPo+ --100k-- PA0 --47k-- GND  -> ratio = 47/147 = 0.3197
#define VDIV_RATIO    0.3197f
#define VREF_MV       3300
#define ADC_BITS      12
#define LIPO_FULL_MV  4200
#define LIPO_EMPTY_MV 3300

// ---- activity thresholds (mirror collar.py) --------------------------------
#define WALKING_ACCEL_THRESHOLD  1.5f  // g-units RMS above gravity -> walking
#define GRAZING_ACCEL_THRESHOLD  0.3f  // below walking, above -> grazing

// ---- LoRaWAN port assignments -----------------------------------------------
#define LORAWAN_PORT_UPLINK    2
#define LORAWAN_PORT_INTERVAL  1
#define LORAWAN_PORT_REBOOT    99

// ---- payload struct (packed, 16 bytes) -------------------------------------
#pragma pack(push, 1)
struct CollarPayload {
    int32_t  lat_e7;        // latitude x 1e7
    int32_t  lon_e7;        // longitude x 1e7
    int16_t  alt_m;         // altitude metres
    uint8_t  activity_code; // 0=resting 1=grazing 2=walking
    uint8_t  battery_pct;   // 0-100
    uint16_t fix_age_s;     // GPS fix age seconds
    uint16_t uptime_s;      // uptime seconds (wraps)
};
#pragma pack(pop)

static_assert(sizeof(CollarPayload) == 16, "CollarPayload must be exactly 16 bytes");

// ---- module-level state ----------------------------------------------------
static TinyGPSPlus gps;
static MPU6050     imu;
static uint32_t    send_interval_ms = (uint32_t)SEND_INTERVAL_MIN * 60 * 1000;
static uint32_t    boot_time_ms     = 0;

// ---- forward declarations --------------------------------------------------
static uint8_t    measure_battery_pct();
static uint8_t    read_activity_code();
static bool       acquire_gps_fix(uint32_t timeout_ms);
static void       handle_downlink(uint8_t port, uint8_t *data, uint16_t len);
static CollarPayload build_payload();

// ============================================================================
// Setup -- runs once after power-on / wake from reset
// ============================================================================
void setup() {
    boot_time_ms = millis();
    Serial.begin(115200);
    delay(500);
    Serial.println("[SkyHerd] collar firmware v1.0 booting");

    // ---- GPS UART (Serial1 = PA9/PA10 on RAK3172) --------------------------
    Serial1.begin(GPS_UART_BAUD);
    delay(100);
    Serial.println("[GPS] UART ready at " + String(GPS_UART_BAUD));

    // ---- IMU I2C (PB6=SCL, PB7=SDA) ----------------------------------------
    Wire.begin();
    imu.initialize();
    if (!imu.testConnection()) {
        Serial.println("[IMU] MPU-6050 not found -- activity will default to resting");
    } else {
        Serial.println("[IMU] MPU-6050 OK at 0x68");
    }

    // ---- LoRaWAN OTAA join --------------------------------------------------
    // RAK RUI3 API: api.lorawan.appeui / deveui / appkey
    api.lorawan.appeui.set(APP_EUI);
    api.lorawan.deveui.set(DEV_EUI);
    api.lorawan.appkey.set(APP_KEY);
    api.lorawan.band.set(RAK_REGION_US915);
    api.lorawan.deviceClass.set(RAK_LORA_CLASS_A);
    api.lorawan.njm.set(RAK_LORA_OTAA);  // over-the-air activation

    // Register downlink callback
    api.lorawan.registerRecvCallback(handle_downlink);

    Serial.println("[LoRa] starting OTAA join...");
    if (!api.lorawan.join(1, 1, 5, 8)) {  // auto-join, retries=8, timeout=5s each
        Serial.println("[LoRa] join failed -- will retry next cycle");
    }
}

// ============================================================================
// Main loop -- acquire, encode, transmit, sleep
// ============================================================================
void loop() {
    Serial.println("[loop] wake -- acquiring GPS fix");

    // ---- 1. GPS fix ----------------------------------------------------------
    bool has_fix = acquire_gps_fix((uint32_t)GPS_FIX_TIMEOUT_S * 1000);
    if (!has_fix) {
        Serial.println("[GPS] no fix within timeout -- sending with stale/zero coords");
    }

    // ---- 2. Build and encode payload ----------------------------------------
    CollarPayload pkt = build_payload();

    Serial.printf("[payload] lat=%.7f lon=%.7f alt=%dm act=%d bat=%d%% fix_age=%ds\n",
        pkt.lat_e7 / 1e7, pkt.lon_e7 / 1e7, (int)pkt.alt_m,
        pkt.activity_code, pkt.battery_pct, pkt.fix_age_s);

    // ---- 3. LoRaWAN uplink (unconfirmed, port 2) ----------------------------
    api.lorawan.send(sizeof(pkt),
                     reinterpret_cast<uint8_t*>(&pkt),
                     LORAWAN_PORT_UPLINK,
                     false,   // unconfirmed
                     0);      // fport retry 0 = no retry

    Serial.println("[LoRa] uplink sent -- sleeping " + String(SEND_INTERVAL_MIN) + " min");

    // ---- 4. Deep sleep ------------------------------------------------------
    // RAK RUI3: api.system.sleep.all(ms) puts MCU + SX1262 into deep sleep
    api.system.sleep.all(send_interval_ms);

    // Execution resumes here after wake (STM32WL reset vector via RTC alarm)
}

// ============================================================================
// GPS fix acquisition
// ============================================================================
static bool acquire_gps_fix(uint32_t timeout_ms) {
    uint32_t start = millis();
    while (millis() - start < timeout_ms) {
        while (Serial1.available() > 0) {
            if (gps.encode(Serial1.read())) {
                if (gps.location.isValid() && gps.location.age() < 2000) {
                    Serial.printf("[GPS] fix acquired in %lums -- sats=%d hdop=%.1f\n",
                        millis() - start,
                        gps.satellites.value(),
                        gps.hdop.hdop());
                    return true;
                }
            }
        }
        delay(10);
    }
    return false;
}

// ============================================================================
// Activity classification from MPU-6050 accel RMS over IMU_ACTIVITY_WINDOW_S
// 0=resting  1=grazing  2=walking   (mirrors collar.py _classify_activity)
// ============================================================================
static uint8_t read_activity_code() {
    if (!imu.testConnection()) {
        return 0;  // resting by default if IMU absent
    }

    // Sample accelerometer for IMU_ACTIVITY_WINDOW_S seconds
    int16_t ax, ay, az, gx, gy, gz;
    float   accel_sum = 0.0f;
    int     samples   = 0;
    uint32_t end_ms   = millis() + (uint32_t)IMU_ACTIVITY_WINDOW_S * 1000;

    while (millis() < end_ms) {
        imu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

        // Convert raw to g (+/-2g range -> 16384 LSB/g)
        float ax_g = ax / 16384.0f;
        float ay_g = ay / 16384.0f;
        float az_g = az / 16384.0f;

        // RMS magnitude of dynamic acceleration (subtract 1g gravity from Z)
        float dyn = sqrtf(ax_g*ax_g + ay_g*ay_g + (az_g - 1.0f)*(az_g - 1.0f));
        accel_sum += dyn;
        samples++;
        delay(50);  // 20 Hz sample rate
    }

    float rms = (samples > 0) ? (accel_sum / samples) : 0.0f;

    if (rms >= WALKING_ACCEL_THRESHOLD) {
        return 2;  // walking
    }
    if (rms >= GRAZING_ACCEL_THRESHOLD) {
        return 1;  // grazing
    }
    return 0;  // resting
}

// ============================================================================
// Battery ADC measurement
// LiPo+ --100k-- PA0 --47k-- GND   (VDIV_RATIO = 0.3197)
// ============================================================================
static uint8_t measure_battery_pct() {
    // RAK RUI3 ADC: api.system.bat.get() returns voltage in mV (if available)
    // Fallback: raw 12-bit ADC on PA0
    uint16_t raw = analogRead(PA0);  // 0-4095
    uint32_t v_pa0_mv = (uint32_t)raw * VREF_MV / ((1 << ADC_BITS) - 1);
    uint32_t v_bat_mv = (uint32_t)(v_pa0_mv / VDIV_RATIO);

    // Clamp and map to 0-100%
    if (v_bat_mv >= LIPO_FULL_MV)  return 100;
    if (v_bat_mv <= LIPO_EMPTY_MV) return 0;
    return (uint8_t)((v_bat_mv - LIPO_EMPTY_MV) * 100 / (LIPO_FULL_MV - LIPO_EMPTY_MV));
}

// ============================================================================
// Build the 16-byte uplink payload
// ============================================================================
static CollarPayload build_payload() {
    CollarPayload p{};

    // GPS fields
    if (gps.location.isValid()) {
        p.lat_e7  = (int32_t)(gps.location.lat() * 1e7);
        p.lon_e7  = (int32_t)(gps.location.lng() * 1e7);
        p.alt_m   = (int16_t)(gps.altitude.meters());
        p.fix_age_s = (uint16_t)min((uint32_t)65535, gps.location.age() / 1000UL);
    } else {
        // No fix -- zeros, fix_age maxed out
        p.lat_e7  = 0;
        p.lon_e7  = 0;
        p.alt_m   = 0;
        p.fix_age_s = 65535;
    }

    p.activity_code = read_activity_code();
    p.battery_pct   = measure_battery_pct();
    p.uptime_s      = (uint16_t)min((uint32_t)65535, (millis() - boot_time_ms) / 1000UL);

    return p;
}

// ============================================================================
// Downlink handler
// Port 1  -> payload[0] = new interval in minutes (1-240)
// Port 99 -> reboot (no payload required)
// ============================================================================
static void handle_downlink(uint8_t port, uint8_t *data, uint16_t len) {
    Serial.printf("[downlink] port=%d len=%d\n", port, len);

    if (port == LORAWAN_PORT_INTERVAL && len >= 1) {
        uint8_t new_min = data[0];
        if (new_min >= 1 && new_min <= 240) {
            send_interval_ms = (uint32_t)new_min * 60 * 1000;
            Serial.printf("[downlink] interval updated to %d min\n", new_min);
        }
    } else if (port == LORAWAN_PORT_REBOOT) {
        Serial.println("[downlink] reboot commanded");
        delay(200);
        api.system.reboot();
    }
}

// ============================================================================
// OTA scaffold (RAK3172 supports BLE DFU in RUI3 bootloader)
// Uncomment and implement when RAK BLE OTA library is stable.
// ============================================================================
#ifdef OTA_ENABLED
  // TODO: initialise RAK BLE OTA service
  // api.ble.advertise.start(30000);  // advertise 30s on boot
  // Firmware images delivered as 256-byte LoRa downlink fragments -- TBD
#endif
