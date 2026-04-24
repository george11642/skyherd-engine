"""Structural tests for ``docker-compose.hardware-demo.yml``.

Validates that the compose file parses as YAML, declares the six expected
services, wires the shared MQTT URL across every service, and gates the
pi-to-mission service on both mosquitto and sitl.  Pure YAML-shape checks —
no docker engine required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = REPO_ROOT / "docker-compose.hardware-demo.yml"
DOCKERFILE_PATH = REPO_ROOT / "docker" / "hardware-demo-edge.Dockerfile"

EXPECTED_SERVICES = {
    "mosquitto",
    "sitl",
    "skyherd-live",
    "skyherd-edge-coyote",
    "skyherd-pi-to-mission",
    "skyherd-speaker",
}


@pytest.fixture(scope="module")
def compose() -> dict:
    assert COMPOSE_PATH.exists(), f"{COMPOSE_PATH} missing"
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))


class TestComposeStructure:
    def test_yaml_parses(self, compose: dict) -> None:
        assert isinstance(compose, dict)
        assert "services" in compose

    def test_all_expected_services_present(self, compose: dict) -> None:
        services = set(compose["services"].keys())
        assert EXPECTED_SERVICES.issubset(services), (
            f"missing services: {EXPECTED_SERVICES - services}"
        )

    def test_mqtt_url_propagates_to_all_needed_services(self, compose: dict) -> None:
        for name in (
            "skyherd-live",
            "skyherd-edge-coyote",
            "skyherd-pi-to-mission",
            "skyherd-speaker",
        ):
            env = compose["services"][name].get("environment", {})
            assert env.get("MQTT_URL") == "mqtt://mosquitto:1883", (
                f"{name}: MQTT_URL missing or wrong"
            )

    def test_ranch_id_propagates(self, compose: dict) -> None:
        for name in (
            "skyherd-live",
            "skyherd-edge-coyote",
            "skyherd-pi-to-mission",
            "skyherd-speaker",
        ):
            env = compose["services"][name].get("environment", {})
            assert env.get("RANCH_ID") == "ranch_a"

    def test_pi_to_mission_depends_on_mosquitto_and_sitl(self, compose: dict) -> None:
        depends = compose["services"]["skyherd-pi-to-mission"].get("depends_on", [])
        # depends_on may be list form or dict form
        if isinstance(depends, dict):
            depends = list(depends.keys())
        assert "mosquitto" in depends
        assert "sitl" in depends

    def test_sitl_exposes_14540_udp(self, compose: dict) -> None:
        ports = compose["services"]["sitl"].get("ports", [])
        udp_ports = [p for p in ports if isinstance(p, str) and "14540" in p]
        assert udp_ports, "sitl must expose 14540/udp for MAVLink"

    def test_skyherd_live_exposes_8000(self, compose: dict) -> None:
        ports = compose["services"]["skyherd-live"].get("ports", [])
        assert any("8000" in str(p) for p in ports)

    def test_speaker_is_muted_in_container(self, compose: dict) -> None:
        env = compose["services"]["skyherd-speaker"].get("environment", {})
        assert env.get("SKYHERD_DETERRENT") == "mute"

    def test_sitl_image_has_override_env_hook(self, compose: dict) -> None:
        raw = COMPOSE_PATH.read_text(encoding="utf-8")
        assert "${SITL_IMAGE:-" in raw, "must expose SITL_IMAGE override"


class TestDockerfileStructure:
    def test_dockerfile_exists(self) -> None:
        assert DOCKERFILE_PATH.exists()

    def test_dockerfile_uses_python311(self) -> None:
        content = DOCKERFILE_PATH.read_text(encoding="utf-8")
        assert "FROM python:3.11" in content

    def test_dockerfile_installs_uv(self) -> None:
        content = DOCKERFILE_PATH.read_text(encoding="utf-8")
        assert "astral.sh/uv" in content

    def test_dockerfile_exposes_8000(self) -> None:
        content = DOCKERFILE_PATH.read_text(encoding="utf-8")
        assert "EXPOSE 8000" in content


class TestMakefileTargets:
    def test_hardware_demo_sim_target_present(self) -> None:
        makefile = REPO_ROOT / "Makefile"
        content = makefile.read_text(encoding="utf-8")
        assert "hardware-demo-sim:" in content
        assert "hardware-demo-sim-down:" in content
        assert "h2-smoke:" in content

    def test_phony_includes_new_targets(self) -> None:
        makefile = REPO_ROOT / "Makefile"
        content = makefile.read_text(encoding="utf-8")
        phony_line = next(
            line for line in content.splitlines() if line.startswith(".PHONY:")
        )
        for tgt in ("hardware-demo-sim", "hardware-demo-sim-down", "h2-smoke"):
            assert tgt in phony_line
