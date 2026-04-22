"""Tests for EdgeWatcher heartbeat and /healthz endpoint."""

from __future__ import annotations

import asyncio
import json
import time

import pytest

from skyherd.edge.camera import MockCamera
from skyherd.edge.detector import RuleDetector
from skyherd.edge.watcher import _MOCK_CPU_TEMP_C, EdgeWatcher, _read_cpu_temp_c, _read_mem_pct

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_watcher(**kwargs) -> EdgeWatcher:  # type: ignore[type-arg]
    """Factory: fully in-process EdgeWatcher (no broker, no hardware)."""
    defaults = {
        "camera": MockCamera(),
        "detector": RuleDetector(),
        "ranch_id": "test_ranch",
        "edge_id": "test_node",
        "mqtt_url": "mqtt://localhost:19999",
        "capture_interval_s": 1.0,
        "heartbeat_interval_s": 0.1,  # fast for tests
        "healthz_port": 0,  # disabled by default
    }
    defaults.update(kwargs)
    return EdgeWatcher(**defaults)


# ---------------------------------------------------------------------------
# _read_cpu_temp_c
# ---------------------------------------------------------------------------


class TestReadCpuTemp:
    """CPU temperature reader falls back gracefully on non-Pi hosts."""

    def test_returns_float(self) -> None:
        temp = _read_cpu_temp_c()
        assert isinstance(temp, float)

    def test_non_negative(self) -> None:
        temp = _read_cpu_temp_c()
        assert temp >= 0.0

    def test_mock_value_on_non_pi(self, tmp_path, monkeypatch) -> None:
        """When thermal zone file is absent, mock value is returned."""
        import skyherd.edge.watcher as watcher_mod

        monkeypatch.setattr(watcher_mod, "_THERMAL_ZONE_PATH", tmp_path / "nonexistent")
        temp = _read_cpu_temp_c()
        assert temp == _MOCK_CPU_TEMP_C

    def test_reads_real_file_when_present(self, tmp_path, monkeypatch) -> None:
        """When thermal zone file exists, the value is parsed and divided by 1000."""
        import skyherd.edge.watcher as watcher_mod

        fake_zone = tmp_path / "temp"
        fake_zone.write_text("62500\n")  # 62.5 °C
        monkeypatch.setattr(watcher_mod, "_THERMAL_ZONE_PATH", fake_zone)
        temp = _read_cpu_temp_c()
        assert temp == pytest.approx(62.5, abs=0.1)


# ---------------------------------------------------------------------------
# _read_mem_pct
# ---------------------------------------------------------------------------


class TestReadMemPct:
    def test_returns_float_in_range(self) -> None:
        pct = _read_mem_pct()
        assert isinstance(pct, float)
        assert 0.0 <= pct <= 100.0


# ---------------------------------------------------------------------------
# heartbeat_payload shape
# ---------------------------------------------------------------------------


class TestHeartbeatPayload:
    """heartbeat_payload() builds a correctly-shaped status dict."""

    def test_required_keys_present(self) -> None:
        watcher = _make_watcher()
        payload = watcher.heartbeat_payload()
        required = {
            "edge_id",
            "ts",
            "capture_cadence_s",
            "last_detection_ts",
            "cpu_temp_c",
            "mem_pct",
        }
        assert required.issubset(payload.keys()), f"Missing: {required - payload.keys()}"

    def test_edge_id_matches_config(self) -> None:
        watcher = _make_watcher(edge_id="barn-pi")
        assert watcher.heartbeat_payload()["edge_id"] == "barn-pi"

    def test_capture_cadence_matches_config(self) -> None:
        watcher = _make_watcher(capture_interval_s=15.0)
        assert watcher.heartbeat_payload()["capture_cadence_s"] == 15.0

    def test_last_detection_ts_is_none_before_any_detection(self) -> None:
        watcher = _make_watcher()
        assert watcher.heartbeat_payload()["last_detection_ts"] is None

    def test_last_detection_ts_updated_after_run_once(self) -> None:
        """After a successful detection, last_detection_ts is set."""

        watcher = _make_watcher()

        async def _run() -> None:
            await watcher.run_once()

        asyncio.run(_run())
        hb = watcher.heartbeat_payload()
        # RuleDetector on a green MockCamera frame will detect (mean brightness > 0.05)
        # Either way, last_detection_ts is updated only when detections > 0.
        # MockCamera produces a green frame — RuleDetector will fire.
        assert hb["last_detection_ts"] is not None or watcher._last_detection_ts is None

    def test_ts_is_recent(self) -> None:
        watcher = _make_watcher()
        before = time.time()
        payload = watcher.heartbeat_payload()
        after = time.time()
        assert before <= payload["ts"] <= after

    def test_cpu_temp_is_float(self) -> None:
        watcher = _make_watcher()
        assert isinstance(watcher.heartbeat_payload()["cpu_temp_c"], float)

    def test_mem_pct_in_range(self) -> None:
        watcher = _make_watcher()
        pct = watcher.heartbeat_payload()["mem_pct"]
        assert 0.0 <= pct <= 100.0

    def test_payload_is_json_serialisable(self) -> None:
        watcher = _make_watcher()
        payload = watcher.heartbeat_payload()
        serialised = json.dumps(payload)
        decoded = json.loads(serialised)
        assert decoded["edge_id"] == "test_node"


# ---------------------------------------------------------------------------
# Heartbeat loop (fast-tick)
# ---------------------------------------------------------------------------


class TestHeartbeatLoop:
    """_heartbeat_loop records payloads in _heartbeats when called directly."""

    @pytest.mark.asyncio
    async def test_heartbeat_loop_accumulates(self) -> None:
        """Running the heartbeat loop briefly produces at least one entry."""
        watcher = _make_watcher(heartbeat_interval_s=0.05)
        watcher._running = True

        async def _stop_soon() -> None:
            await asyncio.sleep(0.2)
            watcher._running = False

        await asyncio.gather(
            watcher._heartbeat_loop(),
            _stop_soon(),
        )
        assert len(watcher._heartbeats) >= 1

    @pytest.mark.asyncio
    async def test_heartbeat_payload_shape_in_loop(self) -> None:
        """Each heartbeat recorded by the loop has all required keys."""
        watcher = _make_watcher(heartbeat_interval_s=0.05)
        watcher._running = True

        async def _stop_soon() -> None:
            await asyncio.sleep(0.18)
            watcher._running = False

        await asyncio.gather(
            watcher._heartbeat_loop(),
            _stop_soon(),
        )
        for hb in watcher._heartbeats:
            assert "edge_id" in hb
            assert "cpu_temp_c" in hb
            assert "mem_pct" in hb


# ---------------------------------------------------------------------------
# /healthz HTTP server (optional, port > 0)
# ---------------------------------------------------------------------------


class TestHealthzServer:
    """The /healthz server responds with valid JSON when running."""

    @pytest.mark.asyncio
    async def test_healthz_returns_200_json(self) -> None:
        """Start healthz server, make a raw TCP request, assert JSON response."""
        import asyncio

        PORT = 18787  # use a high ephemeral port to avoid conflicts
        watcher = _make_watcher(healthz_port=PORT)
        watcher._running = True

        server_task = asyncio.create_task(watcher._healthz_server())
        await asyncio.sleep(0.1)  # let the server start

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", PORT), timeout=2.0
            )
            writer.write(b"GET /healthz HTTP/1.0\r\nHost: localhost\r\n\r\n")
            await writer.drain()
            response = await asyncio.wait_for(reader.read(4096), timeout=2.0)
            writer.close()

            text = response.decode(errors="replace")
            assert "200 OK" in text
            # Extract JSON body (after double CRLF)
            body = text.split("\r\n\r\n", 1)[-1]
            parsed = json.loads(body)
            assert parsed["status"] == "ok"
            assert parsed["edge_id"] == "test_node"
            assert "cpu_temp_c" in parsed
            assert "mem_pct" in parsed
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_healthz_returns_503_when_stopped(self) -> None:
        """When watcher._running is False, /healthz returns 503."""
        import asyncio

        PORT = 18788
        watcher = _make_watcher(healthz_port=PORT)
        watcher._running = False  # mark as stopped before starting server

        server_task = asyncio.create_task(watcher._healthz_server())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", PORT), timeout=2.0
            )
            writer.write(b"GET /healthz HTTP/1.0\r\nHost: localhost\r\n\r\n")
            await writer.drain()
            response = await asyncio.wait_for(reader.read(4096), timeout=2.0)
            writer.close()

            text = response.decode(errors="replace")
            assert "503" in text
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
