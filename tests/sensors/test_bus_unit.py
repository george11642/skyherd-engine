"""Unit tests for SensorBus helpers that don't require a real MQTT broker."""

from __future__ import annotations

from skyherd.sensors.bus import SensorBus, _canonical_json


def test_parse_url_standard() -> None:
    """mqtt://host:port is parsed correctly."""
    host, port = SensorBus._parse_url("mqtt://mybroker:1884")
    assert host == "mybroker"
    assert port == 1884


def test_parse_url_no_port() -> None:
    """URL without port defaults to 1883."""
    host, port = SensorBus._parse_url("mqtt://mybroker")
    assert host == "mybroker"
    assert port == 1883


def test_parse_url_just_host() -> None:
    """Bare hostname (no scheme) defaults to 1883."""
    host, port = SensorBus._parse_url("localhost")
    assert host == "localhost"
    assert port == 1883


def test_canonical_json_sorted_keys() -> None:
    """canonical_json produces sorted keys."""
    payload = {"z": 1, "a": 2, "m": 3}
    result = _canonical_json(payload)
    assert result == '{"a":2,"m":3,"z":1}'


def test_canonical_json_compact() -> None:
    """No extra whitespace in canonical JSON."""
    result = _canonical_json({"key": "value"})
    assert " " not in result


def test_sensor_bus_external_url(monkeypatch) -> None:
    """When MQTT_URL is set, embedded broker is not used."""
    monkeypatch.setenv("MQTT_URL", "mqtt://external:1883")
    bus = SensorBus()
    assert bus._use_embedded is False
    assert bus._host == "external"


def test_sensor_bus_no_url_uses_embedded(monkeypatch) -> None:
    """When MQTT_URL is absent, embedded broker is selected."""
    monkeypatch.delenv("MQTT_URL", raising=False)
    bus = SensorBus()
    assert bus._use_embedded is True
