# Bill of Materials — SkyHerd LoRa GPS Cattle Collar

**Total estimated cost: ~$52**  (prices as of Q2 2026, USD)

---

## Core Electronics

| Part | Description | Price | Supplier | Part Number |
|------|-------------|-------|----------|-------------|
| RAK3172 | SX1262 LoRaWAN module, STM32WL53, IPEX connector | ~$10 | [RAKwireless store](https://store.rakwireless.com/products/wisduo-lpwan-module-rak3172) / DigiKey | RAK3172 / 4711 |
| MAX-M10S breakout | u-blox M10 GPS, UART, 3.3V, 18×18mm footprint | ~$12 | [SparkFun GPS-18037](https://www.sparkfun.com/products/18037) / Mouser 713-GPS-18037 | SFE-GPS-18037 |
| MPU-6050 breakout | InvenSense 6-axis IMU, I²C, 3.3/5V tolerant | ~$3 | Amazon / AliExpress GY-521 board | GY-521 |
| TP4056 charger | LiPo 1S charger + protection, micro-USB or USB-C | ~$2 | Amazon / AliExpress 5-pack ~$6 | TP4056-TYPE-C |
| 2500 mAh LiPo | 3.7V single-cell, ~60×40×8mm flat pack | ~$10 | Adafruit 328 / Mouser / HobbyKing | ADA-328 |
| LoRa antenna | 915 MHz quarter-wave whip, IPEX/SMA pigtail | ~$3 | Amazon / AliExpress | — |

## Enclosure & Mounting

| Part | Description | Price | Notes |
|------|-------------|-------|-------|
| PETG filament (spool) | ~30g per collar shell | ~$2 | Any brand; PETG preferred over PLA for UV/moisture resistance |
| Cattle strap | 1.5" nylon adjustable neck strap, stainless buckle | ~$5 | Local feed store or Amazon farm supply |
| Silicone gasket material | 2mm strip, cut-to-length for IP65 seal | ~$2 | Amazon O-ring cord stock |
| M2×6 stainless screws | 4× for lid, 2× for PCB standoffs | ~$1 | Hardware store |
| Kapton tape / heat shrink | Insulate battery leads + strain relief | ~$2 | Electronics supply |

**Subtotal: ~$52**

---

## Alternatives if primary parts unavailable

| Scenario | Alternative | Notes |
|----------|-------------|-------|
| RAK3172 out of stock | **Heltec ESP32 LoRa V3** (SX1262 + ESP32-S3, ~$8) | Requires PlatformIO `espressif32` platform instead of `ststm32`; firmware `#ifdef HELTEC_ESP32` branch included in `main.cpp` |
| MAX-M10S out of stock | **u-blox NEO-M8N** module (~$10, eBay/AliExpress) | Same UART NMEA protocol; UBX-NAV-PVT still available; slightly larger 25×35mm PCB |
| Local LoRa coverage needed | **RAK7289 outdoor 8-channel gateway** (~$199) or **Mikrotik wAP LR8 kit** (~$120) | Best coverage for NM ranch; mount on grain bin or water tower |

---

## Optional coprocessor (not required for MVP)

The RAK3172 STM32WL53 MCU has sufficient flash (256 KB) and RAM (64 KB) for the MVP firmware. An ESP32-S3 coprocessor (~$5) would add OTA firmware update via BLE, edge ML inferencing, and a second UART for richer sensor fusion — but is explicitly **not** part of the Tier H4 MVP.

---

## DigiKey part search

Search `RAK3172` at [digikey.com](https://www.digikey.com) → filter manufacturer "RAKwireless Technology". The module is also available through the [RAKwireless Aliexpress store](https://www.aliexpress.com/store/2014386) in 5-packs (~$38) if ordering multiple collars.
