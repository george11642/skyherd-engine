# Bill of Materials — SkyHerd LoRa GPS Cattle Collar

**Retail total: ~$75 with shipping.  Bulk AliExpress total: ~$58.**
(Prices as of Q2 2026, USD.)

---

## Core Electronics

| Skip? | Part | Description | Price | Supplier | Part Number |
|-------|------|-------------|-------|----------|-------------|
| N | RAK3172 | SX1262 LoRaWAN module, STM32WL53, IPEX connector | ~$10 | [store.rakwireless.com/products/wisduo-lpwan-module-rak3172](https://store.rakwireless.com/products/wisduo-lpwan-module-rak3172) / DigiKey | RAK3172 / 4711 |
| N | MAX-M10S breakout | u-blox M10 GPS, UART, 3.3V, 18×18mm footprint | ~$12 | [sparkfun.com/products/18037](https://www.sparkfun.com/products/18037) / Mouser 713-GPS-18037 | SFE-GPS-18037 |
| N | MPU-6050 breakout | InvenSense 6-axis IMU, I²C, 3.3/5V tolerant (GY-521 board) | ~$3 | [aliexpress.com/item/32340949017](https://www.aliexpress.com/item/32340949017.html) | GY-521 |
| N | TP4056 charger | LiPo 1S charger + protection, USB-C | ~$2 | [amazon.com/dp/B07K8BCRJH](https://www.amazon.com/dp/B07K8BCRJH) (5-pack ~$6) | TP4056-TYPE-C |
| N | 2500 mAh LiPo | 3.7V single-cell, ~60×40×8mm flat pack | ~$10 | [adafruit.com/product/328](https://www.adafruit.com/product/328) / HobbyKing | ADA-328 |
| N | LoRa antenna | 915 MHz, 3 dBi, SMA-M + IPEX pigtail | ~$3 | [amazon.com/dp/B07R2ZLTWP](https://www.amazon.com/dp/B07R2ZLTWP) | — |
| Y | Status LED | 3 mm green, 10 kΩ resistor — helps debug JOIN/uplink | ~$0.50 | Any electronics shop | — |
| Y | 2N7000 N-FET | Switches GPS VCC for power-gating (saves ~30 mA sleep) | ~$0.20 | DigiKey / Mouser | 2N7000-ND |

## Enclosure & Mounting

| Skip? | Part | Description | Price | Notes |
|-------|------|-------------|-------|-------|
| N | PETG filament | ~30 g per collar shell | ~$2 | Any brand; PETG preferred over PLA for UV/moisture resistance |
| N | Cattle strap | 1.5" nylon adjustable neck strap, stainless buckle | ~$5 | Local feed store or Amazon farm supply |
| N | Silicone gasket | 2 mm strip, cut-to-length for IP65 seal | ~$2 | O-ring cord stock |
| N | M2 × 6 stainless screws | 4× lid, 2× PCB standoffs | ~$1 | Hardware store |
| Y | Kapton tape / heat shrink | Battery lead insulation + strain relief | ~$2 | Nice-to-have for longevity |

**Subtotal: ~$52**

### Shipping estimate

| Supplier | Lead time | Shipping cost |
|----------|-----------|---------------|
| Adafruit (LiPo) | 3–5 days US | ~$8 |
| SparkFun (GPS) | 2–3 days US | ~$6 |
| AliExpress (IMU, TP4056, antenna) | 2–4 weeks | Free / $2 express |
| DigiKey / Mouser | 1–2 days (Prime-equivalent) | ~$10 |
| Amazon (LiPo charger, antenna) | 1–2 days Prime | free with Prime |

**Total with shipping (retail):** ~$75.
**Total with shipping (bulk via AliExpress store):** ~$58 per unit when ordering 5+.

---

## LoRaWAN regulatory note

The default firmware builds for **US915** (PlatformIO flag `-D LORAWAN_REGION_US915`). Shipping or operating a US915 collar in **EU868 / AS923 / AU915** regions is not legal and will not work — the antenna, channel plan, and duty cycle limits differ.

To switch regions:

1. Change the antenna to a matching-frequency version (e.g. a 868 MHz whip for EU).
2. Update `build_flags` in `firmware/platformio.ini`: replace `LORAWAN_REGION_US915` with the target region macro (RAK RUI3 supports `RAK_REGION_EU868`, `RAK_REGION_AS923`, `RAK_REGION_AU915`, `RAK_REGION_IN865`, `RAK_REGION_KR920`).
3. Re-provision the ChirpStack device profile for the new region.
4. Do **not** cross national borders with a collar powered on — national spectrum authorities enforce.

---

## Alternatives if primary parts unavailable

| Scenario | Alternative | Notes |
|----------|-------------|-------|
| RAK3172 out of stock | **Heltec ESP32 LoRa V3** (SX1262 + ESP32-S3, ~$8) | Build env `heltec` in `platformio.ini`; firmware `#ifdef HELTEC_ESP32` branch compiles without changes |
| MAX-M10S out of stock | **u-blox NEO-M8N** module (~$10, eBay/AliExpress) | Same UART NMEA protocol; UBX-NAV-PVT still available; slightly larger 25×35 mm PCB |
| Local LoRa coverage needed | **RAK7289 outdoor 8-channel gateway** (~$199) or **Mikrotik wAP LR8 kit** (~$120) | Best coverage for NM ranch; mount on grain bin or water tower |
| Low-budget gateway | **Raspberry Pi + RAK2245 Pi HAT** (~$130 incl. Pi) | DIY gateway; worse weatherproofing but swap-capable |

---

## Provisioning checklist

Before first flash on a fresh unit, have these ready:

- [ ] DevEUI (16 hex chars, from ChirpStack device page)
- [ ] AppEUI (16 hex chars, your application's JoinEUI)
- [ ] AppKey (32 hex chars, shared OTAA secret)
- [ ] Ranch ID + cow tag to map to the DevEUI
- [ ] ChirpStack v4 instance reachable over MQTT
- [ ] Mosquitto broker reachable (for SkyHerd side)
- [ ] Battery at > 50 % charge (fresh-from-the-factory LiPos usually ship at ~40 %)

Then run:

```bash
./hardware/collar/flash.sh
python hardware/collar/provisioning/register-collar.py \
    --dev-eui A8610A3453210A00 \
    --ranch ranch_a \
    --cow-tag A001
```

---

## Optional coprocessor (not required for MVP)

The RAK3172 STM32WL53 MCU has sufficient flash (256 KB) and RAM (64 KB) for the MVP firmware. An ESP32-S3 coprocessor (~$5) would add OTA firmware update via BLE, edge ML inferencing, and a second UART for richer sensor fusion — but is explicitly **not** part of the Tier H4 MVP.

---

## DigiKey part search

Search `RAK3172` at [digikey.com](https://www.digikey.com) → filter manufacturer "RAKwireless Technology". The module is also available through the [RAKwireless Aliexpress store](https://www.aliexpress.com/store/2014386) in 5-packs (~$38) if ordering multiple collars.
