/**
 * PlatformIO unit tests for CollarPayload encoding/decoding.
 * Run on host platform: pio test -e native
 *
 * Tests validate:
 *  - Struct is exactly 16 bytes (packed)
 *  - Round-trip encode->decode preserves all fields
 *  - Activity codes match collar.py _classify_activity thresholds
 *  - Battery ADC mapping to percentage
 *  - Boundary values (zero coords, maxed fix_age, uptime wrap)
 */

#include <unity.h>
#include <stdint.h>
#include <string.h>
#include <cmath>
#include <cassert>

// ---- Payload struct (must match main.cpp exactly) --------------------------
#pragma pack(push, 1)
struct CollarPayload {
    int32_t  lat_e7;
    int32_t  lon_e7;
    int16_t  alt_m;
    uint8_t  activity_code;
    uint8_t  battery_pct;
    uint16_t fix_age_s;
    uint16_t uptime_s;
};
#pragma pack(pop)

// ---- Activity classification (mirrors collar.py + main.cpp) ----------------
static const float WALKING_ACCEL_THRESHOLD = 1.5f;
static const float GRAZING_ACCEL_THRESHOLD = 0.3f;

static uint8_t classify_activity(float accel_rms) {
    if (accel_rms >= WALKING_ACCEL_THRESHOLD) return 2;
    if (accel_rms >= GRAZING_ACCEL_THRESHOLD) return 1;
    return 0;
}

// ---- Battery ADC mapping ---------------------------------------------------
static const float VDIV_RATIO    = 0.3197f;
static const int   VREF_MV       = 3300;
static const int   ADC_BITS      = 12;
static const int   LIPO_FULL_MV  = 4200;
static const int   LIPO_EMPTY_MV = 3300;

static uint8_t adc_to_battery_pct(uint16_t raw_adc) {
    uint32_t v_pa0_mv = (uint32_t)raw_adc * VREF_MV / ((1 << ADC_BITS) - 1);
    uint32_t v_bat_mv = (uint32_t)((float)v_pa0_mv / VDIV_RATIO);
    if (v_bat_mv >= (uint32_t)LIPO_FULL_MV)  return 100;
    if (v_bat_mv <= (uint32_t)LIPO_EMPTY_MV) return 0;
    return (uint8_t)((v_bat_mv - LIPO_EMPTY_MV) * 100 / (LIPO_FULL_MV - LIPO_EMPTY_MV));
}

// ============================================================================
// Tests
// ============================================================================

void test_payload_size(void) {
    TEST_ASSERT_EQUAL_INT(16, sizeof(CollarPayload));
}

void test_round_trip_typical(void) {
    // Typical NM ranch location
    double lat =  34.052340;
    double lon = -106.534281;

    CollarPayload pkt{};
    pkt.lat_e7        = (int32_t)(lat * 1e7);
    pkt.lon_e7        = (int32_t)(lon * 1e7);
    pkt.alt_m         = 1540;
    pkt.activity_code = 1;   // grazing
    pkt.battery_pct   = 82;
    pkt.fix_age_s     = 3;
    pkt.uptime_s      = 900; // 15 min

    // Serialise to raw bytes
    uint8_t buf[16];
    memcpy(buf, &pkt, 16);

    // Deserialise back
    CollarPayload out{};
    memcpy(&out, buf, 16);

    TEST_ASSERT_EQUAL_INT32(pkt.lat_e7,        out.lat_e7);
    TEST_ASSERT_EQUAL_INT32(pkt.lon_e7,        out.lon_e7);
    TEST_ASSERT_EQUAL_INT16(pkt.alt_m,         out.alt_m);
    TEST_ASSERT_EQUAL_UINT8(pkt.activity_code, out.activity_code);
    TEST_ASSERT_EQUAL_UINT8(pkt.battery_pct,   out.battery_pct);
    TEST_ASSERT_EQUAL_UINT16(pkt.fix_age_s,    out.fix_age_s);
    TEST_ASSERT_EQUAL_UINT16(pkt.uptime_s,     out.uptime_s);
}

void test_round_trip_zero_coords(void) {
    CollarPayload pkt{};
    pkt.lat_e7    = 0;
    pkt.lon_e7    = 0;
    pkt.alt_m     = 0;
    pkt.fix_age_s = 65535; // no fix sentinel

    uint8_t buf[16];
    memcpy(buf, &pkt, 16);
    CollarPayload out{};
    memcpy(&out, buf, 16);

    TEST_ASSERT_EQUAL_INT32(0,     out.lat_e7);
    TEST_ASSERT_EQUAL_INT32(0,     out.lon_e7);
    TEST_ASSERT_EQUAL_UINT16(65535, out.fix_age_s);
}

void test_round_trip_southern_hemisphere(void) {
    // Southern hemisphere -> negative latitude
    double lat = -33.8688;
    double lon =  151.2093;

    CollarPayload pkt{};
    pkt.lat_e7 = (int32_t)(lat * 1e7);
    pkt.lon_e7 = (int32_t)(lon * 1e7);

    uint8_t buf[16];
    memcpy(buf, &pkt, 16);
    CollarPayload out{};
    memcpy(&out, buf, 16);

    TEST_ASSERT_EQUAL_INT32(pkt.lat_e7, out.lat_e7);
    TEST_ASSERT_EQUAL_INT32(pkt.lon_e7, out.lon_e7);

    // Decoded lat should be negative
    double decoded_lat = out.lat_e7 / 1e7;
    TEST_ASSERT_TRUE(decoded_lat < 0.0);
}

void test_activity_resting(void) {
    TEST_ASSERT_EQUAL_UINT8(0, classify_activity(0.0f));
    TEST_ASSERT_EQUAL_UINT8(0, classify_activity(0.1f));
    TEST_ASSERT_EQUAL_UINT8(0, classify_activity(0.29f));
}

void test_activity_grazing(void) {
    TEST_ASSERT_EQUAL_UINT8(1, classify_activity(0.30f));
    TEST_ASSERT_EQUAL_UINT8(1, classify_activity(0.5f));
    TEST_ASSERT_EQUAL_UINT8(1, classify_activity(1.49f));
}

void test_activity_walking(void) {
    TEST_ASSERT_EQUAL_UINT8(2, classify_activity(1.5f));
    TEST_ASSERT_EQUAL_UINT8(2, classify_activity(2.0f));
    TEST_ASSERT_EQUAL_UINT8(2, classify_activity(10.0f));
}

void test_battery_full(void) {
    // ADC at LIPO_FULL_MV after divider: raw = LIPO_FULL_MV * VDIV / VREF * 4095
    // v_pa0 = LIPO_FULL_MV * VDIV_RATIO = 4200 * 0.3197 ~= 1343 mV
    // raw = 1343 * 4095 / 3300 ~= 1665
    uint16_t raw_full = 1665;
    uint8_t pct = adc_to_battery_pct(raw_full);
    TEST_ASSERT_EQUAL_UINT8(100, pct);
}

void test_battery_empty(void) {
    // v_pa0 = 3300 * 0.3197 ~= 1055 mV  -> raw ~= 1309
    // Values below this should clamp to 0
    uint16_t raw_empty = 1000; // well below empty threshold
    uint8_t pct = adc_to_battery_pct(raw_empty);
    TEST_ASSERT_EQUAL_UINT8(0, pct);
}

void test_battery_midpoint(void) {
    // v_bat = (FULL + EMPTY)/2 = 3750 mV -> v_pa0 = 3750 * 0.3197 ~= 1199 mV
    // raw ~= 1487
    uint16_t raw_mid = 1487;
    uint8_t pct = adc_to_battery_pct(raw_mid);
    // Should be roughly 50% (+/-5% due to integer rounding)
    TEST_ASSERT_UINT8_WITHIN(5, 50, pct);
}

void test_uptime_wrap(void) {
    // uptime_s is uint16 -- ensure it wraps correctly
    CollarPayload pkt{};
    pkt.uptime_s = 65535;

    uint8_t buf[16];
    memcpy(buf, &pkt, 16);
    CollarPayload out{};
    memcpy(&out, buf, 16);

    TEST_ASSERT_EQUAL_UINT16(65535, out.uptime_s);
}

void test_payload_byte_order_little_endian(void) {
    // lat_e7 = 0x01020304 should appear as 04 03 02 01 in buffer
    CollarPayload pkt{};
    pkt.lat_e7 = 0x01020304;

    uint8_t buf[16];
    memcpy(buf, &pkt, 16);

    TEST_ASSERT_EQUAL_UINT8(0x04, buf[0]);
    TEST_ASSERT_EQUAL_UINT8(0x03, buf[1]);
    TEST_ASSERT_EQUAL_UINT8(0x02, buf[2]);
    TEST_ASSERT_EQUAL_UINT8(0x01, buf[3]);
}

// ============================================================================
int main(void) {
    UNITY_BEGIN();

    RUN_TEST(test_payload_size);
    RUN_TEST(test_round_trip_typical);
    RUN_TEST(test_round_trip_zero_coords);
    RUN_TEST(test_round_trip_southern_hemisphere);
    RUN_TEST(test_activity_resting);
    RUN_TEST(test_activity_grazing);
    RUN_TEST(test_activity_walking);
    RUN_TEST(test_battery_full);
    RUN_TEST(test_battery_empty);
    RUN_TEST(test_battery_midpoint);
    RUN_TEST(test_uptime_wrap);
    RUN_TEST(test_payload_byte_order_little_endian);

    return UNITY_END();
}
