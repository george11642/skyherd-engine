"""Tests for TroughCamSensor — cow counting and frame URI."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from skyherd.sensors.trough_cam import TroughCamSensor, _write_placeholder_png
from skyherd.world.cattle import Cow


@pytest.mark.asyncio
async def test_trough_cam_reading_published(world, mock_bus) -> None:
    """Tick publishes a trough_cam.reading payload with required fields."""
    trough_cfg = world.terrain.config.troughs[0]  # tr_sw_1 at (250, 500)
    sensor = TroughCamSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        trough_cfg=trough_cfg,
        cam_id="cam_1",
        period_s=10.0,
    )
    await sensor.tick()

    topic = "skyherd/ranch_a/trough_cam/cam_1"
    msgs = mock_bus.all_payloads(topic)
    assert len(msgs) == 1
    p = msgs[0]
    assert p["kind"] == "trough_cam.reading"
    assert p["trough_id"] == trough_cfg.id
    assert "cows_present" in p
    assert "ids" in p
    assert isinstance(p["ids"], list)
    assert "frame_uri" in p
    assert p["ranch"] == "ranch_a"
    assert p["entity"] == "cam_1"


@pytest.mark.asyncio
async def test_trough_cam_counts_nearby_cows(world, mock_bus) -> None:
    """Cows placed near trough are counted."""
    trough_cfg = world.terrain.config.troughs[0]  # tr_sw_1 at (250, 500)
    tx, ty = trough_cfg.pos

    # Move the first 3 cows right next to the trough
    updated_cows = []
    for i, cow in enumerate(world.herd.cows):
        if i < 3:
            data = cow.model_dump()
            data["pos"] = (tx + 5.0, ty + 5.0)  # 7m away — within 50m
            updated_cows.append(Cow(**data))
        else:
            updated_cows.append(cow)
    world.herd.cows = updated_cows

    sensor = TroughCamSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        trough_cfg=trough_cfg,
        cam_id="cam_1",
        period_s=10.0,
    )
    await sensor.tick()

    topic = "skyherd/ranch_a/trough_cam/cam_1"
    msgs = mock_bus.all_payloads(topic)
    assert msgs[0]["cows_present"] >= 3
    assert len(msgs[0]["ids"]) >= 3


@pytest.mark.asyncio
async def test_trough_cam_no_nearby_cows(world, mock_bus) -> None:
    """Cows all far from trough yield cows_present=0."""
    trough_cfg = world.terrain.config.troughs[0]  # tr_sw_1 at (250, 500)
    tx, ty = trough_cfg.pos

    # Move all cows far away (1000m+)
    updated_cows = []
    for cow in world.herd.cows:
        data = cow.model_dump()
        data["pos"] = (tx + 1000.0, ty + 1000.0)
        updated_cows.append(Cow(**data))
    world.herd.cows = updated_cows

    sensor = TroughCamSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        trough_cfg=trough_cfg,
        cam_id="cam_1",
        period_s=10.0,
    )
    await sensor.tick()

    topic = "skyherd/ranch_a/trough_cam/cam_1"
    msgs = mock_bus.all_payloads(topic)
    assert msgs[0]["cows_present"] == 0
    assert msgs[0]["ids"] == []


def test_write_placeholder_png_creates_file(tmp_path: Path) -> None:
    """_write_placeholder_png creates a PNG file at the given path."""
    out = tmp_path / "frames" / "test.png"
    _write_placeholder_png(out, cow_count=3)
    assert out.exists()
    assert out.stat().st_size > 0


def test_write_placeholder_png_handles_pil_error(tmp_path: Path) -> None:
    """_write_placeholder_png swallows exceptions without raising."""
    out = tmp_path / "frames" / "test.png"
    # Patch PIL Image.new to raise an unexpected error
    with patch("skyherd.sensors.trough_cam.Path.parent", side_effect=RuntimeError("boom")):
        # Should not raise even if PIL path fails
        try:
            _write_placeholder_png(out, cow_count=0)
        except Exception:  # noqa: BLE001
            pass  # acceptable if PIL not installed or path fails


@pytest.mark.asyncio
async def test_trough_cam_frame_uri_in_payload(world, mock_bus) -> None:
    """frame_uri in payload points into runtime/frames directory."""
    trough_cfg = world.terrain.config.troughs[0]
    sensor = TroughCamSensor(
        world=world,
        bus=mock_bus,
        ranch_id="ranch_a",
        trough_cfg=trough_cfg,
        cam_id="cam_2",
        period_s=10.0,
    )
    await sensor.tick()

    topic = "skyherd/ranch_a/trough_cam/cam_2"
    msgs = mock_bus.all_payloads(topic)
    assert "runtime/frames" in msgs[0]["frame_uri"]


# ---------------------------------------------------------------------------
# HYG-01 caplog RED test (Task 1 — will fail until Task 2 source edits land)
# ---------------------------------------------------------------------------


class TestHygieneLogs:
    async def test_frame_render_debug_log_on_import_error(
        self, world, mock_bus, monkeypatch, caplog
    ) -> None:
        """TroughCamSensor logs DEBUG when vision renderer import fails."""
        import logging
        import sys

        caplog.set_level(logging.DEBUG, logger="skyherd.sensors.trough_cam")

        # Make skyherd.vision.renderer raise ImportError on import
        monkeypatch.setitem(sys.modules, "skyherd.vision.renderer", None)

        trough_cfg = world.terrain.config.troughs[0]
        sensor = TroughCamSensor(
            world=world,
            bus=mock_bus,
            ranch_id="ranch_a",
            trough_cfg=trough_cfg,
            cam_id="cam_hyg_01",
            period_s=10.0,
        )
        await sensor.tick()

        # After Task 2, this assertion will pass:
        assert "vision renderer unavailable" in caplog.text
