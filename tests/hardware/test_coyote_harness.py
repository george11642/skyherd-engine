"""Tests for CoyoteHarness — thermal clip playback + MQTT emission.

Exercises clip loading, deterministic frame-index cycling, canonical JSON
schema, dual-topic fan-out, lifecycle, and CLI subcommand.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from skyherd.edge.cli import app
from skyherd.edge.coyote_harness import (
    CoyoteHarness,
    _canonical_json,
    _parse_mqtt_url,
)

runner = CliRunner(mix_stderr=False)


def _fixed_ts() -> float:
    """Fixed timestamp provider — supports byte-level determinism assertions."""
    return 1_714_000_000.0


# ---------------------------------------------------------------------------
# Clip loading
# ---------------------------------------------------------------------------


class TestClipLoading:
    def test_default_dir_loads_six_frames(self) -> None:
        harness = CoyoteHarness(seed=42)
        assert len(harness._clip_frames) == 6
        for p in harness._clip_frames:
            assert p.exists()
            assert p.suffix == ".png"

    def test_explicit_clip_dir_is_used(self, tmp_path: Path) -> None:
        # Put 3 PNG stubs in tmp_path
        from skyherd.edge.fixtures.picam._generate import generate as gen

        gen(tmp_path)
        harness = CoyoteHarness(clip_dir=tmp_path)
        # picam fixtures are 4 frames by default
        assert len(harness._clip_frames) == 4

    def test_raises_on_missing_dir(self, tmp_path: Path) -> None:
        ghost = tmp_path / "no_such"
        with pytest.raises(FileNotFoundError):
            CoyoteHarness(clip_dir=ghost)

    def test_raises_on_empty_dir(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("not a png")
        with pytest.raises(ValueError):
            CoyoteHarness(clip_dir=tmp_path)

    def test_skips_non_png_files(self, tmp_path: Path) -> None:
        # Copy just frame 0 from default fixtures + add a .txt sibling
        from tests.fixtures.thermal_clips._generate import generate as gen

        gen(tmp_path)
        (tmp_path / "README.txt").write_text("ignore me")
        harness = CoyoteHarness(clip_dir=tmp_path)
        # 6 PNGs preserved, non-PNG ignored
        assert len(harness._clip_frames) == 6


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_reading_kind_is_thermal_reading(self) -> None:
        harness = CoyoteHarness(ts_provider=_fixed_ts)
        reading = asyncio.run(harness.run_once())
        assert reading["kind"] == "thermal.reading"

    def test_reading_contains_hits_list(self) -> None:
        harness = CoyoteHarness(ts_provider=_fixed_ts)
        reading = asyncio.run(harness.run_once())
        assert "hits" in reading
        assert reading["predators_detected"] == 1
        assert len(reading["hits"]) == 1

    def test_reading_includes_ranch_entity_cam_pos(self) -> None:
        harness = CoyoteHarness(ranch_id="ranch_x", cam_id="coyote_7", ts_provider=_fixed_ts)
        reading = asyncio.run(harness.run_once())
        assert reading["ranch"] == "ranch_x"
        assert reading["entity"] == "coyote_7"
        assert reading["cam_pos"] == [0.0, 0.0]

    def test_thermal_hit_alert_has_species_signature(self) -> None:
        captured: list[tuple[str, bytes]] = []

        async def cap(topic: str, raw: bytes) -> None:
            captured.append((topic, raw))

        harness = CoyoteHarness(mqtt_publish=cap, ts_provider=_fixed_ts)
        asyncio.run(harness.run_once())
        # Reading topic + thermal_hit topic both captured
        assert len(captured) == 2
        alert_topic = f"skyherd/{harness._ranch_id}/alert/thermal_hit"
        alerts = [json.loads(raw) for topic, raw in captured if topic == alert_topic]
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["kind"] == "predator.thermal_hit"
        assert alert["species"] == "coyote"
        assert alert["thermal_signature"] == 0.78

    def test_source_is_cardboard_coyote(self) -> None:
        harness = CoyoteHarness(ts_provider=_fixed_ts)
        reading = asyncio.run(harness.run_once())
        assert reading["source"] == "cardboard_coyote"

    def test_frame_path_is_absolute_and_exists(self) -> None:
        harness = CoyoteHarness(ts_provider=_fixed_ts)
        reading = asyncio.run(harness.run_once())
        assert "frame_path" in reading
        assert Path(reading["frame_path"]).exists()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_seeded_mode_identical_sequence_across_instances(self) -> None:
        def seq(seed: int, n: int) -> list[int]:
            h = CoyoteHarness(seed=seed, ts_provider=_fixed_ts)
            out: list[int] = []
            for _ in range(n):
                r = asyncio.run(h.run_once())
                out.append(r["frame_idx"])
            return out

        assert seq(42, 10) == seq(42, 10)

    def test_different_seeds_differ(self) -> None:
        def seq(seed: int, n: int) -> list[int]:
            h = CoyoteHarness(seed=seed, ts_provider=_fixed_ts)
            out: list[int] = []
            for _ in range(n):
                r = asyncio.run(h.run_once())
                out.append(r["frame_idx"])
            return out

        assert seq(42, 6) != seq(43, 6)

    def test_unseeded_cycles_modulo(self) -> None:
        h = CoyoteHarness(ts_provider=_fixed_ts)  # seed=None
        seq: list[int] = []
        for _ in range(7):
            r = asyncio.run(h.run_once())
            seq.append(r["frame_idx"])
        # 6-frame clip: expect 0,1,2,3,4,5,0
        assert seq == [0, 1, 2, 3, 4, 5, 0]

    def test_canonical_json_is_sort_keys_compact(self) -> None:
        payload = {"b": 2, "a": 1, "c": [1, 2]}
        raw = _canonical_json(payload)
        assert raw == '{"a":1,"b":2,"c":[1,2]}'

    def test_fixed_ts_provider_makes_payload_byte_stable(self) -> None:
        # Two harnesses, same seed, same ts_provider → byte-identical json
        captured1: list[bytes] = []
        captured2: list[bytes] = []

        async def cap1(topic: str, raw: bytes) -> None:  # noqa: ARG001
            captured1.append(raw)

        async def cap2(topic: str, raw: bytes) -> None:  # noqa: ARG001
            captured2.append(raw)

        h1 = CoyoteHarness(seed=42, ts_provider=_fixed_ts, mqtt_publish=cap1)
        h2 = CoyoteHarness(seed=42, ts_provider=_fixed_ts, mqtt_publish=cap2)
        for _ in range(3):
            asyncio.run(h1.run_once())
            asyncio.run(h2.run_once())
        assert captured1 == captured2


# ---------------------------------------------------------------------------
# Publish paths
# ---------------------------------------------------------------------------


class TestPublish:
    def test_injected_publisher_receives_reading_and_alert(self) -> None:
        captured: list[tuple[str, bytes]] = []

        async def cap(topic: str, raw: bytes) -> None:
            captured.append((topic, raw))

        h = CoyoteHarness(mqtt_publish=cap, ts_provider=_fixed_ts)
        asyncio.run(h.run_once())
        topics = [t for t, _ in captured]
        assert f"skyherd/{h._ranch_id}/thermal/{h._cam_id}" in topics
        assert f"skyherd/{h._ranch_id}/alert/thermal_hit" in topics

    def test_publisher_failure_does_not_raise(self) -> None:
        async def fail(topic: str, raw: bytes) -> None:  # noqa: ARG001
            raise ConnectionError("boom")

        h = CoyoteHarness(mqtt_publish=fail, ts_provider=_fixed_ts)
        reading = asyncio.run(h.run_once())
        assert reading["kind"] == "thermal.reading"

    def test_default_path_swallows_unreachable_broker(self) -> None:
        h = CoyoteHarness(mqtt_url="mqtt://localhost:19999", ts_provider=_fixed_ts)
        reading = asyncio.run(h.run_once())
        assert reading["kind"] == "thermal.reading"


class TestMqttUrlParse:
    def test_parse_host_port(self) -> None:
        assert _parse_mqtt_url("mqtt://10.0.0.1:1884") == ("10.0.0.1", 1884)

    def test_parse_no_port_defaults_1883(self) -> None:
        host, port = _parse_mqtt_url("mqtt://hosty")
        assert host == "hosty"
        assert port == 1883

    def test_parse_invalid_port_defaults_1883(self) -> None:
        host, port = _parse_mqtt_url("mqtt://hostx:notaport")
        assert port == 1883


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_stop_ends_run_loop(self) -> None:
        h = CoyoteHarness(interval_s=0.01, ts_provider=_fixed_ts)

        async def go() -> None:
            task = asyncio.create_task(h.run())
            await asyncio.sleep(0.05)
            h.stop()
            await asyncio.wait_for(task, timeout=1.0)

        asyncio.run(go())
        assert not h._running

    def test_max_ticks_pattern_exits(self) -> None:
        h = CoyoteHarness(ts_provider=_fixed_ts, seed=42)

        async def bounded(n: int) -> int:
            for _ in range(n):
                await h.run_once()
            return h._tick_count

        ticks = asyncio.run(bounded(4))
        assert ticks == 4
        assert len(h._published_readings) == 4
        assert len(h._published_alerts) == 4


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCli:
    def test_coyote_runs_one_tick(self) -> None:
        result = runner.invoke(app, ["coyote", "--max-ticks", "1", "--seed", "42"])
        assert result.exit_code == 0, result.output + (result.stderr or "")
        combined = result.output + (result.stderr or "")
        assert "coyote tick" in combined

    def test_coyote_seed_flag_forwards(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from skyherd.edge import coyote_harness as ch

        captured: dict[str, Any] = {}
        orig_init = ch.CoyoteHarness.__init__

        def spy_init(self: Any, *args: Any, **kwargs: Any) -> None:
            captured["seed"] = kwargs.get("seed")
            captured["species"] = kwargs.get("species")
            orig_init(self, *args, **kwargs)

        monkeypatch.setattr(ch.CoyoteHarness, "__init__", spy_init)
        result = runner.invoke(
            app,
            [
                "coyote",
                "--max-ticks",
                "1",
                "--seed",
                "77",
                "--species",
                "wolf",
            ],
        )
        assert result.exit_code == 0
        assert captured["seed"] == 77
        assert captured["species"] == "wolf"


# ---------------------------------------------------------------------------
# Re-export shim
# ---------------------------------------------------------------------------


class TestHardwareShim:
    def test_hardware_cardboard_coyote_imports_same_class(self) -> None:
        from hardware.cardboard_coyote.coyote_harness import CoyoteHarness as Shim

        assert Shim is CoyoteHarness
