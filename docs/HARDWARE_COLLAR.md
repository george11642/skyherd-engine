# Hardware Collar Runbook — SkyHerd Tier H4

End-to-end guide from parts order to dashboard confirmation.

---

## 1. Order parts

See `hardware/collar/BOM.md` for the complete bill of materials (~$52).

Key items:
- **RAK3172** SX1262 LoRaWAN module — [RAKwireless store](https://store.rakwireless.com/products/wisduo-lpwan-module-rak3172) or DigiKey
- **MAX-M10S** GPS breakout — SparkFun GPS-18037 or Mouser equivalent
- **MPU-6050** IMU breakout — Amazon GY-521 board (~$3)
- **2500mAh LiPo** + TP4056 USB-C charger board
- **915 MHz whip antenna** (IPEX to SMA pigtail)
- PETG filament, cattle strap, M2 screws, silicone gasket strip

Allow 1–5 days domestic shipping (SparkFun + DigiKey typically 2-day).

---

## 2. Print the shell

Requires OpenSCAD and a FDM printer (PETG recommended).

```bash
# Regenerate STL from parametric SCAD source
make -C hardware/collar shell
# Output: hardware/collar/3d_print/collar_shell.stl
#         hardware/collar/3d_print/collar_lid.stl
```

**Slicer settings (PrusaSlicer / Bambu Studio):**
- Layer height: 0.2 mm
- Walls: 3 perimeters
- Infill: 30% gyroid
- Supports: tree supports for strap slot overhangs only
- Temperature: 240°C nozzle / 80°C bed (PETG)
- Estimated print time: ~3.5h per shell

Fit silicone gasket (2mm × 2.5mm strip) around lid groove before closing.

---

## 3. Wire the electronics

Follow `hardware/collar/wiring.md` and `hardware/collar/wiring.ascii`.

Quick summary:
- RAK3172 UART1 (PA9/PA10) → u-blox MAX-M10S GPS RX/TX
- RAK3172 I²C (PB6/PB7) → MPU-6050 SCL/SDA
- LiPo → TP4056 → LDO 3.3V → RAK3172 VDD, GPS VCC, IMU VCC
- Voltage divider (100kΩ/47kΩ) on PA0 for battery ADC
- 915 MHz whip through top-wall antenna slot

---

## 4. Configure secrets

```bash
cp hardware/collar/firmware/include/secrets.h.example \
   hardware/collar/firmware/include/secrets.h
```

Edit `secrets.h` with your ChirpStack credentials:
- `DEV_EUI` — printed on RAK3172 module label
- `APP_EUI` — from ChirpStack application
- `APP_KEY` — from ChirpStack device OTAA credentials

---

## 5. Build and flash firmware

PlatformIO must be installed (`pip install platformio` or [platformio.org](https://platformio.org)).

```bash
cd hardware/collar

# Compile
make build

# Put RAK3172 into DFU mode: hold BOOT pin, press RESET, release BOOT
# Then upload:
make flash

# Verify with serial monitor (115200 baud):
make monitor
```

Expected boot output:
```
[SkyHerd] collar firmware v1.0 booting
[GPS] UART ready at 9600
[IMU] MPU-6050 OK at 0x68
[LoRa] starting OTAA join…
```

**Docker alternative (no local PlatformIO needed):**
```bash
docker run --rm -v $(pwd)/hardware/collar/firmware:/workspace \
  platformio/platformio:latest pio run
```

---

## 6. Provision the collar

```bash
# Set ChirpStack credentials (optional — falls back to local registry)
export CHIRPSTACK_API_URL=http://localhost:8080
export CHIRPSTACK_API_TOKEN=<your-token>

python hardware/collar/provisioning/register-collar.py \
    --dev-eui A8610A3453210A00 \
    --ranch ranch_a \
    --cow-tag A001
```

This:
1. Registers the device in ChirpStack via REST API (if env vars set)
2. Writes `runtime/collars/registry.json`
3. Verifies MQTT broker connectivity

---

## 7. Configure ChirpStack HTTP integration

In ChirpStack UI → Application → Integrations → HTTP:
- **Event endpoint URL:** `http://localhost:8001/lorawan/uplink`
- **Headers:** `X-SkyHerd-Secret: <shared secret>`

The decoder at `hardware/collar/provisioning/decode_payload.py` handles the uplink:
```bash
# Test manually with a captured hex payload:
python hardware/collar/provisioning/decode_payload.py \
    39e46414d4b5e4c10c0601520300840e \
    --ranch ranch_a --cow-tag A001 --publish
```

---

## 8. Verify on dashboard

1. Start the sim engine: `make sim`
2. Open dashboard: `make dashboard` → [http://localhost:8000](http://localhost:8000)
3. Cow A001 should appear as a **green** dot (real hardware) instead of pink (sim)
4. Subscribe to confirm live uplinks:
   ```bash
   mosquitto_sub -t 'skyherd/ranch_a/collar/A001' -v
   ```

---

## 9. Known-good LoRa gateways (US 915 MHz)

| Gateway | Cost | Notes |
|---------|------|-------|
| **RAK7289** outdoor 8-channel | ~$199 | Weatherproof, ideal for NM ranch, PoE |
| **Mikrotik wAP LR8** kit | ~$120 | Compact, indoor/sheltered mount |
| **RAK7244** Raspberry Pi HAT | ~$99 | Good for lab testing only |

Mount gateway on grain bin roof, water tower, or barn peak — aim for 5–10m elevation. In flat NM terrain a single RAK7289 covers ~10km radius.

---

## 10. Run firmware unit tests (no hardware needed)

```bash
make -C hardware/collar test
# Or run Python-side tests:
uv run pytest -q tests/hardware/
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `[GPS] no fix within timeout` | Move outdoors, clear sky view. Cold start can take 90s. |
| `[LoRa] join failed` | Check DEV_EUI/APP_EUI/APP_KEY in secrets.h match ChirpStack |
| `[IMU] MPU-6050 not found` | Check I²C wiring; confirm AD0 pulled to GND (addr 0x68) |
| Dashboard shows cow as pink (sim) | Check registry.json `source` field is `"real"` |
| No uplinks in ChirpStack | Verify gateway is registered and online; check US915 sub-band |
