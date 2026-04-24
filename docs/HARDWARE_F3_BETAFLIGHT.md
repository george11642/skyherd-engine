# HARDWARE_F3_BETAFLIGHT.md — DIY quad motor beat

**What this is:** a hackathon-demo shim that spins the motors on a
bench-mounted SP Racing F3 flight controller (Betaflight or iNav) for
~2 seconds when a Managed Agent dispatches the drone. It is **not** autonomous
flight — the quad stays bolted to the bench. The effect is a loud, obvious
"dispatch acknowledged" beat for the 3-minute demo video.

Backend class: `skyherd.drone.betaflight_override.BetaflightOverrideBackend`

---

## SAFETY — READ BEFORE POWERING THE QUAD

> **NO PROPELLERS. Ever. Indoors, always. Even for the test run.**
>
> Racing motors at 30% throttle will launch a mis-balanced prop into a wall,
> ceiling, camera, or face in under a second. The `--test` harness prints a
> banner reminding you of this before sending any MSP frame. Do not skip the
> banner.

Hardware-level belt-and-braces:

1. **Hard timeout.** Every spin call is wrapped in
   `asyncio.wait_for(..., timeout=SKYHERD_MOTOR_SPIN_TIMEOUT_S)` and clamped
   to `MAX_SPIN_TIMEOUT_S = 10.0s` at the code level. A stuck coroutine
   cannot leave motors spinning past that ceiling.
2. **Motors-zero on every exit path.** `try/finally` around the spin loop,
   `__aexit__` of the async context manager, and `disconnect()` all emit a
   `MSP_SET_MOTOR` frame with all 8 motors set to 0 (stopped).
3. **Throttle ceiling.** `SKYHERD_MOTOR_THROTTLE_US` is clamped to
   `MAX_THROTTLE_US = 1300us` (~30% of full throttle) at the code level.
   A bad env var cannot full-send the motors.
4. **Betaflight failsafe.** Configure `msp_override_failsafe=ON` so that
   when MSP frames stop arriving for ~200 ms, the flight controller cuts
   motors on its own. This is the hardware-level backstop if the software
   hangs.
5. **Dry run.** `--dry-run` prints MSP frames to stdout without opening the
   serial port. Use it to sanity-check the bytes before plugging the quad in.

If anything looks wrong, unplug the LiPo. The motors have no standalone
power source.

---

## One-command bench test

```bash
# With a Betaflight/iNav F3 connected via micro-USB, NO PROPELLERS, LiPo in hand:
uv sync --extra drone-hw                    # installs pyserial
make drone-betaflight-smoke                 # spins motor 0 at 1200us for 2s
```

Equivalent explicit invocation:

```bash
SKYHERD_DRONE_BACKEND=betaflight \
uv run python -m skyherd.drone.betaflight_override --test --port /dev/ttyACM0
```

Add `--dry-run` to see the MSP frames without touching the hardware.

---

## Betaflight / iNav configuration

You need the flight controller to accept `MSP_SET_MOTOR` while **disarmed**.
That's non-default — by default Betaflight refuses motor commands unless the
arm switch is flipped.

**Betaflight (≥4.3):**

1. Open Betaflight Configurator → **Motors** tab.
2. Enable the "I understand the risks" toggle.
3. In the CLI, run:
   ```
   set motor_output_disarmed_passthrough = ON
   save
   ```
4. Reboot the FC. Verify with `get motor_output_disarmed_passthrough` — should
   read `ON`.

**iNav (≥7.0):**

1. Open iNav Configurator → **Motors** tab.
2. Enable "MSP motor passthrough".
3. In the CLI:
   ```
   set msp_override_channels = MOTOR_PASSTHROUGH
   save
   ```

If `MSP_SET_MOTOR` has no effect in your build, the runbook's fallback is the
CLI path: send `motor 0 1200\n`, wait `duration`, send `motor 0 1000\n`,
`exit\n`. That path is not implemented here — if you need it, open an issue
against the backend module.

---

## Serial port setup

The F3 enumerates as a USB CDC device:

| OS | Device pattern | Typical name |
|---|---|---|
| Linux (including Pi) | `/dev/ttyACM*` | `/dev/ttyACM0` |
| macOS | `/dev/cu.usbmodem*` | `/dev/cu.usbmodem14401` |
| Windows | `COM*` | `COM3`, `COM4`, ... |

On Linux, add your user to the `dialout` group once:

```bash
sudo usermod -aG dialout "$USER"
# log out and back in
```

Port auto-detection order:

1. `SKYHERD_F3_PORT` env var (used verbatim).
2. Glob `/dev/ttyACM*` (Linux) or `/dev/cu.usbmodem*` (macOS) — first match.
3. `serial.tools.list_ports.comports()` filtered for `STM32` / `Betaflight`
   / `Virtual COM` / `CDC` in the description (Windows).
4. Raises `DroneUnavailable` if nothing matches.

---

## Environment variables

| Variable | Default | Clamped to | Meaning |
|---|---|---|---|
| `SKYHERD_F3_PORT` | (auto-detect) | — | Serial device path override |
| `SKYHERD_MOTOR_SPIN_TIMEOUT_S` | `5.0` | `[0.1, 10.0]` | Hard ceiling for every spin call |
| `SKYHERD_MOTOR_THROTTLE_US` | `1200` | `[1000, 1300]` | Motor throttle microseconds |
| `SKYHERD_DRONE_BACKEND` | `sitl` | — | Set to `betaflight` to select this backend |
| `DRONE_BACKEND` | `sitl` | — | Legacy alias; `SKYHERD_DRONE_BACKEND` wins |

---

## MQTT / agent dispatch path

When the `FenceLineDispatcher` agent decides to dispatch a drone, the
`drone_dispatch` MQTT topic (or in-process dispatch queue) invokes the
`DroneBackend` resolved by the factory. To route dispatches to the F3:

```bash
# In the shell that runs `make demo` or `skyherd-demo`:
export SKYHERD_DRONE_BACKEND=betaflight
export SKYHERD_F3_PORT=/dev/ttyACM0  # optional; auto-detect usually works

make demo SEED=42 SCENARIO=coyote    # fires FenceLineDispatcher → this backend
```

The factory call site is
`skyherd.drone.interface.get_backend()` — it lazy-imports
`BetaflightOverrideBackend` when `SKYHERD_DRONE_BACKEND=betaflight`.

---

## Troubleshooting

**`DroneUnavailable: No serial device found for Betaflight F3.`**
The quad isn't plugged in, or `dialout` group membership hasn't taken effect
(log out and back in). Check:
```bash
ls -l /dev/ttyACM*           # Linux
ls -l /dev/cu.usbmodem*      # macOS
python -m serial.tools.list_ports -v   # all OSes
```

**Motors don't spin when `--test` runs.**
Almost always: `motor_output_disarmed_passthrough` isn't set. Re-run the
Betaflight CLI commands above and reboot. Double-check by watching the
Configurator's Motors tab — moving the sliders there proves the FC accepts
motor commands disarmed.

**Windows doesn't enumerate the F3 as a COM port.**
Install the [STM32 Virtual COM Port driver](https://www.st.com/en/development-tools/stsw-stm32102.html).
After install, the FC should appear as `STMicroelectronics Virtual COM Port`
in Device Manager.

**`uv run pytest` reports async tests unsupported.**
Run with the dev extra loaded:
```bash
uv run --extra dev --extra drone-hw pytest tests/drone/test_betaflight_override.py
```

**I want to test without plugging in the quad.**
```bash
uv run python -m skyherd.drone.betaflight_override --test --dry-run
```
Every MSP frame is logged in hex; no serial port is opened.
