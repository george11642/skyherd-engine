/**
 * SkyHerd DIY LoRa GPS Cattle Collar — Firmware (polished Apr 2026)
 * Target: RAK3172 (STM32WL53 + SX1262) running RAK RUI3
 *
 * ─── PIN MAP (RAK3172 WisBlock pinout) ──────────────────────────────────────
 *   GPS UART (Serial1)  : PA9 (TX) / PA10 (RX)   @ 9600 baud NMEA
 *   IMU I²C (Wire)      : PB6 (SCL) / PB7 (SDA)  @ 0x68  (MPU-6050)
 *   Battery ADC         : PA0  (voltage divider 100k/47k, VDIV_RATIO=0.3197)
 *   GPS power control   : PA2  (MOSFET gate, HIGH=ON) — optional, see GPS_PWR_PIN
 *   LED (status, opt.)  : PA8  (board-LED; toggled on uplink)
 *
 * ─── POWER TREE ─────────────────────────────────────────────────────────────
 *   LiPo 3.7V 2500 mAh
 *     └─► TP4056 charger + protection
 *           └─► 3V3 LDO (on RAK3172 module, ~50 µA quiescent)
 *                 ├─► RAK3172 STM32WL + SX1262
 *                 ├─► u-blox MAX-M10S GPS  (via MOSFET @ PA2, OFF during sleep)
 *                 └─► MPU-6050 IMU         (3.3V, I²C pull-ups on board)
 *
 * ─── POWER BUDGET (15-min cycle, grazing mode, US915 SF7) ───────────────────
 *   Active uplink window   ≈ 102 s total:
 *     90 s  GPS fix (~30 mA avg, cold-to-warm)
 *     10 s  IMU sampling   (~4 mA)
 *      2 s  LoRa TX         (~100 mA peak, 800 ms actual airtime)
 *   Deep sleep               ≈ 798 s @ ~10 µA (MCU+SX1262+GPS-OFF)
 *   Average draw             ≈ 3.7 mA → ~675 h ≈ 28 days on 2500 mAh (60% eff.)
 *   With BATSAVE active (1 h cycle): ~8× longer between cycles → ~50 days.
 *
 * ─── LORAWAN ────────────────────────────────────────────────────────────────
 *   Default region   : US915 (set via `-D LORAWAN_REGION_US915`)
 *   Alt regions      : EU868 / AS923 / AU915 — change build flag + antenna.
 *   Class            : A (RX1/RX2 after uplink only; battery optimal)
 *   Join             : OTAA, 8 retries, 5s each
 *   Port 2           : uplink (16-byte CollarPayload)
 *   Port 1 downlink  : set interval (1 byte: minutes 1..240)
 *   Port 99 downlink : reboot
 *
 * ─── BATTERY-SAVE MODE ──────────────────────────────────────────────────────
 *   When battery_pct < LOW_BATTERY_THRESHOLD_PCT (default 15%), the sleep
 *   interval is multiplied by BATSAVE_MULTIPLIER (default 4). This cuts uplink
 *   frequency from 15 min → 1 h, extending runtime until recharge.
 *
 * ─── PAYLOAD LAYOUT (little-endian, 16 bytes — frozen schema v1) ────────────
 *   [0..3]   int32   lat_e7          latitude  x 1e7
 *   [4..7]   int32   lon_e7          longitude x 1e7
 *   [8..9]   int16   alt_m           altitude metres
 *   [10]     uint8   activity_code   0=resting 1=grazing 2=walking
 *   [11]     uint8   battery_pct     0-100
 *   [12..13] uint16  fix_age_s       GPS fix age in seconds (65535 = no fix)
 *   [14..15] uint16  uptime_s        seconds since last boot (wraps 65535)
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
#ifndef BATSAVE_MULTIPLIER
  #define BATSAVE_MULTIPLIER    4   // 4x longer sleep when battery < threshold
#endif
// GPS_PWR_PIN is optional: when defined, the firmware power-gates the GPS.
// Leave undefined on boards without a MOSFET on the GPS VCC rail.

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
static void       gps_power_on();
static void       gps_power_off();

// ============================================================================
// GPS power-gating helpers
//   When GPS_PWR_PIN is defined (e.g. RAK3172 with PA2 driving a MOSFET gate
//   on the GPS VCC rail), we cut power between cycles to save ~30 mA.
//   On boards without the MOSFET, both helpers compile to no-ops.
// ============================================================================
static void gps_power_on() {
#ifdef GPS_PWR_PIN
    pinMode(GPS_PWR_PIN, OUTPUT);
    digitalWrite(GPS_PWR_PIN, HIGH);
    delay(50);  // let GPS LDO settle before UART opens
    // Re-initialise UART after power-cycle (driver may have closed it).
    Serial1.begin(GPS_UART_BAUD);
#endif
}

static void gps_power_off() {
#ifdef GPS_PWR_PIN
    Serial1.end();  // release UART so GPS can brown out cleanly
    digitalWrite(GPS_PWR_PIN, LOW);
#endif
}

// ============================================================================
// Setup -- runs once after power-on / wake from reset
// ============================================================================
void setup() {
    boot_time_ms = millis();
    Serial.begin(115200);
    delay(500);
    Serial.println("[SkyHerd] collar firmware v1.1 booting");

    // ---- GPS power + UART ---------------------------------------------------
    gps_power_on();  // no-op if GPS_PWR_PIN undefined
#ifndef GPS_PWR_PIN
    // Fallback: open UART unconditionally when we're not power-gating.
    Serial1.begin(GPS_UART_BAUD);
#endif
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

    // ---- 0. Re-power GPS on wake (no-op if not power-gated) -----------------
    gps_power_on();

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

    // ---- 4. Battery-save: extend interval when running low ------------------
    uint32_t sleep_ms = send_interval_ms;
    if (pkt.battery_pct < LOW_BATTERY_THRESHOLD_PCT) {
        sleep_ms = send_interval_ms * (uint32_t)BATSAVE_MULTIPLIER;
        Serial.printf("[batsave] battery %d%% < %d%% -- extending interval %dx to %lu ms\n",
                      pkt.battery_pct, LOW_BATTERY_THRESHOLD_PCT,
                      BATSAVE_MULTIPLIER, (unsigned long)sleep_ms);
    }

    Serial.println("[LoRa] uplink sent -- sleeping " + String(sleep_ms / 1000) + " s");

    // ---- 5. Deep sleep (cut GPS power first) --------------------------------
    gps_power_off();
    // RAK RUI3: api.system.sleep.all(ms) puts MCU + SX1262 into deep sleep
    api.system.sleep.all(sleep_ms);

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
// OTA update — sign-post for post-MVP work
//
// When OTA_ENABLED is defined at build time, the firmware will eventually
// support one of two paths. Neither is implemented in v1.1 — both need a real
// RAK3172 to validate and therefore live in `deferred-features.md`.
//
// Path A — LoRaWAN FUOTA (Firmware Update Over The Air)
//   • Uses LoRaWAN class B/C multicast fragments (RFC draft)
//   • RAK RUI3 AT command: `AT+FUOTA=<fragsize>,<blockcnt>,<sessionid>`
//     ref: https://docs.rakwireless.com/RUI3/
//   • Requires ChirpStack FUOTA plug-in + bandwidth budget
//   • TODO: choose between FragmentedDataBlockTransport + McClassC vs
//           application-layer fragments on Port 3.
//   • TODO: integrate `api.system.flashUpdate()` callback
//
// Path B — BLE DFU (RAK bootloader, alt. on ESP32)
//   • RAK RUI3 bootloader advertises a DFU service on reset
//   • ESP32 variant uses `esp_ota_*` via BLE GATT
//   • Requires a phone/laptop within 10 m — demo-only
//   • TODO: RAK BLE OTA example at https://github.com/RAKWireless/WisBlock
//
// For now we advertise neither; OTA is a Phase 10 item.
// ============================================================================
#ifdef OTA_ENABLED
  // Placeholder: leave empty until real hardware is on hand.
  // Uncomment the relevant TODO block above when Path A or Path B is chosen.
#endif
