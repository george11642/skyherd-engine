# Wiring Guide — SkyHerd LoRa GPS Cattle Collar

## Overview

All logic runs at **3.3V**. The TP4056 charger output (4.2V max) feeds a small LDO regulator (HT7333 or MCP1700-3302) to produce a stable 3.3V rail. The RAK3172 module has an internal 3.3V regulator capable of sourcing ~50mA peak (more than enough for MCU + GPS + IMU).

See `wiring.ascii` for the schematic-level ASCII diagram.

---

## Pin Assignments (RAK3172 header)

### UART1 → u-blox MAX-M10S GPS

| RAK3172 pin | GPS pin | Function |
|-------------|---------|----------|
| PA9 (TX1) | RX | MCU → GPS commands |
| PA10 (RX1) | TX | GPS NMEA/UBX → MCU |
| 3V3 | VCC | Power |
| GND | GND | Ground |

Baud rate: **9600** (GPS default); configure to 115200 in firmware after boot for faster fix reporting.

### I²C → MPU-6050 IMU

| RAK3172 pin | MPU-6050 pin | Function |
|-------------|--------------|----------|
| PB6 (SCL) | SCL | I²C clock |
| PB7 (SDA) | SDA | I²C data |
| 3V3 | VCC | Power |
| GND | GND | Ground |
| — | AD0 | Pull to GND → I²C address 0x68 |
| — | INT | Optional — leave unconnected for MVP |

### Battery / Power

| TP4056 pin | Connection | Notes |
|------------|------------|-------|
| BAT+ | LiPo+ | Via JST-PH 2-pin connector |
| BAT− | LiPo− | — |
| OUT+ | 3.3V LDO IN | Then LDO OUT → RAK3172 VDD + GPS VCC + IMU VCC |
| OUT− | GND rail | — |
| IN+ | USB-C 5V (charge) | Or solar panel 5V |

### Battery ADC (voltage monitoring)

Use a **100kΩ / 47kΩ voltage divider** on RAK3172 pin **PA0** (ADC_IN0):
- LiPo+ → 100kΩ → PA0 → 47kΩ → GND
- Divider ratio: 47/(100+47) = 0.320
- Full charge 4.2V → 1.34V on PA0 (within 3.3V ADC range)

---

## Power budget (15-minute sleep cycle)

| Mode | Current | Duration | Energy/cycle |
|------|---------|----------|--------------|
| Deep sleep (MCU+GPS off) | ~10µA | ~14m50s | ~0.025 mAh |
| GPS cold start + fix | ~25mA | ~60s max | ~0.42 mAh |
| MCU active + LoRa TX | ~40mA | ~2s | ~0.022 mAh |
| **Total per 15min cycle** | — | — | **~0.47 mAh** |
| **2500 mAh battery** | — | — | **~5300 cycles ≈ 55 days** |

---

## Notes

- Keep GPS antenna trace away from LoRa antenna — 3cm minimum separation.
- 3D-print shell has a dedicated antenna slot routed out the top (see `collar_shell.scad`).
- Fritzing project file placeholder: `hardware/collar/wiring.fzz` — generate from schematic above using Fritzing desktop app.
