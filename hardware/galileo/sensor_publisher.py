#!/usr/bin/env python3
"""sensor_publisher.py — SkyHerd Galileo `edge-tank` telemetry publisher.

Publishes:
- ``skyherd/{ranch}/edge_status/{edge_id}`` — heartbeat, every HEARTBEAT_INTERVAL_SEC (default 30 s).
- ``skyherd/{ranch}/water_tank/{edge_id}`` — water-tank level, every PUBLISH_INTERVAL_SEC (default 60 s).
- ``skyherd/{ranch}/weather/{edge_id}`` — weather telemetry, every PUBLISH_INTERVAL_SEC (gated on WEATHER_ENABLED).

Runs on the Intel Galileo Gen 1 under Yocto systemd (`skyherd-galileo.service`),
and on a laptop for sim-mode demo fallback. The Gen 1's 400 MHz Quark X1000 and
256 MB RAM mean: no threads, the simpler paho-mqtt callbacks API only, and
single-shot sensor polls — nothing fancy.

Config is read from environment variables (set by systemd from
``/etc/skyherd/galileo.env``):

- MQTT_URL              ``mqtt://host:port`` (required)
- RANCH_ID              e.g. ``ranch_a`` (required)
- EDGE_ID               e.g. ``edge-tank`` (required)
- SENSOR_MODE           ``sim`` (default) or ``real``
- PUBLISH_INTERVAL_SEC  default 60
- HEARTBEAT_INTERVAL_SEC default 30
- TANK_ID               default ``tank_n`` — the tank this node speaks for
- WEATHER_ENABLED       ``1``/``0``, default ``0``
- LOG_LEVEL             default ``INFO``

Payload schemas mirror ``src/skyherd/edge/watcher.py`` (heartbeat) and
``src/skyherd/sensors/water.py`` (water-tank reading) so existing SkyHerd
agents consume Galileo output identically to the Pi edge and sim sensors.
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import signal
import sys
import time

log = logging.getLogger("skyherd-galileo")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_DEFAULT_MQTT_URL = "mqtt://127.0.0.1:1883"
_DEFAULT_PUBLISH_INTERVAL_SEC = 60.0
_DEFAULT_HEARTBEAT_INTERVAL_SEC = 30.0


def _getenv(key: str, default: str | None = None) -> str:
    v = os.environ.get(key)
    if v is None or v == "":
        if default is None:
            log.error("required env var %s is unset", key)
            sys.exit(2)
        return default
    return v


def _getenv_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _getenv_bool(key: str, default: bool = False) -> bool:
    v = os.environ.get(key, "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return default


def _parse_mqtt_url(url: str) -> tuple[str, int]:
    """Parse ``mqtt://host:port`` -> (host, port); default port 1883."""
    without_scheme = url.split("://", 1)[-1]
    if ":" in without_scheme:
        host, port_str = without_scheme.rsplit(":", 1)
        try:
            return host, int(port_str)
        except ValueError:
            pass
    return without_scheme, 1883


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


# ---------------------------------------------------------------------------
# Sensors — sim + optional real via mraa
# ---------------------------------------------------------------------------


class TankLevelSim:
    """Deterministic sinusoidal tank-level trace with gentle noise.

    Range roughly 45 - 85 % with a 30-minute period, ~2 % noise. Good for
    demo recording: produces a visibly falling edge when crossed with the
    water_drop scenario's step-down.
    """

    def __init__(self, seed: int = 42) -> None:
        self._t0 = time.time()
        self._rng = random.Random(seed)

    def read(self) -> float:
        elapsed = time.time() - self._t0
        base = 65.0 + 20.0 * math.sin(elapsed / 1800.0 * 2.0 * math.pi)
        noise = self._rng.uniform(-2.0, 2.0)
        return round(max(0.0, min(100.0, base + noise)), 2)


class WeatherSim:
    """Sim temperature + humidity — slow drift around 65 F / 55 %RH."""

    def __init__(self, seed: int = 43) -> None:
        self._t0 = time.time()
        self._rng = random.Random(seed)

    def read(self) -> tuple[float, float]:
        elapsed = time.time() - self._t0
        temp_f = 65.0 + 8.0 * math.sin(elapsed / 3600.0 * 2.0 * math.pi)
        humidity = 55.0 + 10.0 * math.cos(elapsed / 3600.0 * 2.0 * math.pi)
        temp_f += self._rng.uniform(-0.5, 0.5)
        humidity += self._rng.uniform(-1.0, 1.0)
        return round(temp_f, 1), round(max(0.0, min(100.0, humidity)), 1)


class TankLevelMraa:
    """HC-SR04 ultrasonic on D2 (trig) / D3 (echo) via Intel's mraa library.

    Gen 1 Arduino headers are 3.3 V on input — put a 1k/2k divider on ECHO
    to step the sensor's 5 V logic down. Tank height is read as distance
    from sensor to water surface; level_pct = 100 * (1 - distance/tank_depth).

    This is a stub — enable after you've wired real hardware, replace the
    `_read_distance_cm` body to actually pulse + time the pin, and pass the
    tank's full depth via env (TANK_DEPTH_CM).
    """

    def __init__(self, tank_depth_cm: float = 120.0) -> None:
        # Import mraa lazily so this module still loads on non-Galileo hosts.
        import mraa  # type: ignore[import-not-found]

        self._trig = mraa.Gpio(2)
        self._trig.dir(mraa.DIR_OUT)
        self._echo = mraa.Gpio(3)
        self._echo.dir(mraa.DIR_IN)
        self._tank_depth_cm = tank_depth_cm

    def _read_distance_cm(self) -> float:
        # Real HC-SR04 timing: 10 us TRIG pulse, then measure ECHO high time.
        # Divide microseconds by 58 to get cm. Left as a stub — wire the
        # sensor and flesh this out on-device.
        raise NotImplementedError("HC-SR04 timing loop: wire sensor, then implement")

    def read(self) -> float:
        distance_cm = self._read_distance_cm()
        pct = 100.0 * (1.0 - distance_cm / self._tank_depth_cm)
        return round(max(0.0, min(100.0, pct)), 2)


# ---------------------------------------------------------------------------
# Local metrics (mirror src/skyherd/edge/watcher.py helpers — Linux sysfs)
# ---------------------------------------------------------------------------

_THERMAL_ZONE_PATH = "/sys/class/thermal/thermal_zone0/temp"


def _read_cpu_temp_c() -> float:
    try:
        with open(_THERMAL_ZONE_PATH) as f:
            return round(int(f.read().strip()) / 1000.0, 1)
    except (OSError, ValueError):
        return 46.0  # plausible mock for non-Galileo hosts


def _read_mem_pct() -> float:
    try:
        info: dict[str, int] = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    info[parts[0].rstrip(":")] = int(parts[1])
        total = info.get("MemTotal", 0)
        available = info.get("MemAvailable", 0)
        if total <= 0:
            return 0.0
        return round((total - available) / total * 100.0, 1)
    except (OSError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


class Publisher:
    def __init__(self) -> None:
        self.mqtt_url = _getenv("MQTT_URL", _DEFAULT_MQTT_URL)
        self.ranch_id = _getenv("RANCH_ID")
        self.edge_id = _getenv("EDGE_ID")
        self.sensor_mode = _getenv("SENSOR_MODE", "sim").lower()
        self.publish_interval_s = _getenv_float("PUBLISH_INTERVAL_SEC", _DEFAULT_PUBLISH_INTERVAL_SEC)
        self.heartbeat_interval_s = _getenv_float("HEARTBEAT_INTERVAL_SEC", _DEFAULT_HEARTBEAT_INTERVAL_SEC)
        self.tank_id = _getenv("TANK_ID", "tank_n")
        self.weather_enabled = _getenv_bool("WEATHER_ENABLED", False)

        self.status_topic = f"skyherd/{self.ranch_id}/edge_status/{self.edge_id}"
        self.tank_topic = f"skyherd/{self.ranch_id}/water_tank/{self.edge_id}"
        self.weather_topic = f"skyherd/{self.ranch_id}/weather/{self.edge_id}"

        self._running = True
        self._client = None  # paho client, created in _connect()
        self._tank_sensor = self._build_tank_sensor()
        self._weather_sensor = WeatherSim() if self.weather_enabled else None

    # -- sensor selection -------------------------------------------------

    def _build_tank_sensor(self):
        if self.sensor_mode == "real":
            try:
                return TankLevelMraa()
            except Exception as exc:  # noqa: BLE001
                log.warning("mraa unavailable (%s) — falling back to sim", exc)
        return TankLevelSim()

    # -- mqtt plumbing ----------------------------------------------------

    def _connect(self):
        # Import lazily so module import works on laptops without paho installed.
        import paho.mqtt.client as mqtt  # type: ignore[import-not-found]

        host, port = _parse_mqtt_url(self.mqtt_url)
        client_id = f"skyherd-galileo-{self.edge_id}"

        # Compatibility: newer paho (>=2.0) made callback-API a required arg.
        try:
            client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)  # type: ignore[attr-defined]
        except AttributeError:
            client = mqtt.Client(client_id=client_id)  # type: ignore[call-arg]

        client.connect(host, port, keepalive=60)
        client.loop_start()
        log.info("Connected to MQTT at %s:%d (client_id=%s)", host, port, client_id)
        return client

    def _publish(self, topic: str, payload: dict) -> None:
        assert self._client is not None
        raw = _canonical_json(payload)
        info = self._client.publish(topic, payload=raw, qos=0, retain=False)
        log.debug("→ %s %s", topic, raw)
        if getattr(info, "rc", 0) != 0:
            log.warning("publish returned rc=%s for %s", info.rc, topic)

    # -- payloads (schemas match src/skyherd/edge/watcher.py + water.py) --

    def _heartbeat_payload(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "ts": time.time(),
            "kind": "telemetry",
            "sensor_mode": self.sensor_mode,
            "cpu_temp_c": _read_cpu_temp_c(),
            "mem_pct": _read_mem_pct(),
        }

    def _tank_payload(self, level_pct: float) -> dict:
        return {
            "ts": time.time(),
            "kind": "water_tank.reading",
            "ranch": self.ranch_id,
            "entity": self.edge_id,
            "tank_id": self.tank_id,
            "level_pct": level_pct,
            "source": "galileo",
        }

    def _weather_payload(self, temp_f: float, humidity: float) -> dict:
        return {
            "ts": time.time(),
            "kind": "weather.reading",
            "ranch": self.ranch_id,
            "entity": self.edge_id,
            "temp_f": temp_f,
            "humidity_pct": humidity,
            "source": "galileo",
        }

    # -- main loop --------------------------------------------------------

    def _on_signal(self, _signo, _frame):  # noqa: ANN001
        log.info("signal received — shutting down")
        self._running = False

    def run(self) -> int:
        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGINT, self._on_signal)

        try:
            self._client = self._connect()
        except Exception as exc:  # noqa: BLE001
            log.error("MQTT connect failed: %s", exc)
            return 1

        last_heartbeat = 0.0
        last_publish = 0.0

        log.info(
            "Publishing to status=%s water=%s weather=%s cadence_s=%s heartbeat_s=%s mode=%s",
            self.status_topic,
            self.tank_topic,
            self.weather_topic if self.weather_enabled else "<disabled>",
            self.publish_interval_s,
            self.heartbeat_interval_s,
            self.sensor_mode,
        )

        while self._running:
            now = time.time()

            if now - last_heartbeat >= self.heartbeat_interval_s:
                try:
                    self._publish(self.status_topic, self._heartbeat_payload())
                except Exception as exc:  # noqa: BLE001
                    log.warning("heartbeat publish failed: %s", exc)
                last_heartbeat = now

            if now - last_publish >= self.publish_interval_s:
                try:
                    level_pct = self._tank_sensor.read()
                    self._publish(self.tank_topic, self._tank_payload(level_pct))
                except Exception as exc:  # noqa: BLE001
                    log.warning("tank read/publish failed: %s", exc)
                if self._weather_sensor is not None:
                    try:
                        temp_f, humidity = self._weather_sensor.read()
                        self._publish(self.weather_topic, self._weather_payload(temp_f, humidity))
                    except Exception as exc:  # noqa: BLE001
                        log.warning("weather read/publish failed: %s", exc)
                last_publish = now

            # 1 s tick — tiny poll cadence is fine on Gen 1 (Quark idles well).
            time.sleep(1.0)

        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:  # noqa: BLE001
                pass
        log.info("skyherd-galileo publisher exited cleanly")
        return 0


def _configure_logging() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> int:
    _configure_logging()
    return Publisher().run()


if __name__ == "__main__":
    sys.exit(main())
