"""Unit tests for :class:`skyherd.edge.speaker_bridge.SpeakerBridge`.

Covers backend selection (mute env, missing audio libs, explicit override),
play() happy path + failure path, WAV fixture regeneration determinism, and
run-loop message forwarding.  All tests offline — no audio device touched.
"""

from __future__ import annotations

import asyncio
import builtins
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from skyherd.edge.fixtures.deterrent import _generate as wav_generator
from skyherd.edge.speaker_bridge import (
    DEFAULT_WAV_FIXTURE,
    DeterrentResult,
    SpeakerBridge,
    nop_player,
)

# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------


class TestBackendSelection:
    def test_mute_env_forces_nop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SKYHERD_DETERRENT", "mute")
        bridge = SpeakerBridge(ranch_id="ranch_a")
        assert bridge.init_backend() == "nop"
        assert bridge.backend_name == "nop"

    def test_false_env_value_forces_nop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SKYHERD_DETERRENT", "false")
        bridge = SpeakerBridge(ranch_id="ranch_a")
        assert bridge.init_backend() == "nop"

    def test_zero_env_value_forces_nop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SKYHERD_DETERRENT", "0")
        bridge = SpeakerBridge(ranch_id="ranch_a")
        assert bridge.init_backend() == "nop"

    def test_explicit_nop_backend_name(self) -> None:
        bridge = SpeakerBridge(ranch_id="ranch_a", backend_name="nop")
        assert bridge.init_backend() == "nop"

    def test_explicit_player_overrides_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SKYHERD_DETERRENT", "play")
        captured: list[tuple[Path, int, float]] = []

        def fake(path: Path, tone: int, dur: float) -> DeterrentResult:
            captured.append((path, tone, dur))
            return DeterrentResult(
                played=True,
                tone_hz=tone,
                duration_s=dur,
                backend="injected",
                wav_path=path,
            )

        bridge = SpeakerBridge(ranch_id="ranch_a", player=fake)
        result = bridge.play(12000, 0.1)
        assert result.backend == "injected"
        assert result.played is True
        assert captured == [(DEFAULT_WAV_FIXTURE, 12000, 0.1)]

    def test_no_audio_libs_falls_back_to_nop(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With SKYHERD_DETERRENT=play and both libs unimportable → nop."""
        monkeypatch.setenv("SKYHERD_DETERRENT", "play")
        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name in ("pygame", "simpleaudio"):
                raise ImportError(f"fake: {name} not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        # Make sure cached modules don't short-circuit the import
        monkeypatch.delitem(sys.modules, "pygame", raising=False)
        monkeypatch.delitem(sys.modules, "simpleaudio", raising=False)

        bridge = SpeakerBridge(ranch_id="ranch_a")
        assert bridge.init_backend() == "nop"

    def test_init_backend_is_idempotent(self) -> None:
        bridge = SpeakerBridge(ranch_id="ranch_a", backend_name="nop")
        first = bridge.init_backend()
        second = bridge.init_backend()
        assert first == second == "nop"


# ---------------------------------------------------------------------------
# play()
# ---------------------------------------------------------------------------


class TestPlay:
    def test_nop_returns_played_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SKYHERD_DETERRENT", "mute")
        bridge = SpeakerBridge(ranch_id="ranch_a")
        result = bridge.play(12000, 6.0)
        assert result.played is False
        assert result.backend == "nop"
        assert result.tone_hz == 12000
        assert result.duration_s == 6.0

    def test_injected_player_happy_path(self) -> None:
        calls: list[tuple[Path, int, float]] = []

        def player(path: Path, tone: int, dur: float) -> DeterrentResult:
            calls.append((path, tone, dur))
            return DeterrentResult(
                played=True,
                tone_hz=tone,
                duration_s=dur,
                backend="test",
                wav_path=path,
            )

        bridge = SpeakerBridge(
            ranch_id="ranch_a", backend_name="test", player=player
        )
        result = bridge.play(14000, 0.05)
        assert result.played is True
        assert result.backend == "test"
        assert len(calls) == 1

    def test_injected_player_exception_returns_played_false(self) -> None:
        """The player abstraction is meant to capture exceptions; if a caller
        provides a broken player the bridge must surface the error cleanly."""

        def broken(path: Path, tone: int, dur: float) -> DeterrentResult:
            return DeterrentResult(
                played=False,
                tone_hz=tone,
                duration_s=dur,
                backend="broken",
                wav_path=path,
                error="device busy",
            )

        bridge = SpeakerBridge(
            ranch_id="ranch_a", backend_name="broken", player=broken
        )
        result = bridge.play(12000, 1.0)
        assert result.played is False
        assert result.error == "device busy"

    def test_nop_player_function_direct(self) -> None:
        """Exercise the module-level nop_player directly."""
        path = Path("/nonexistent/path.wav")
        res = nop_player(path, 11000, 3.5)
        assert res.played is False
        assert res.backend == "nop"
        assert res.wav_path == path


# ---------------------------------------------------------------------------
# handle_message
# ---------------------------------------------------------------------------


class TestHandleMessage:
    def test_forwards_matching_topic_to_player(self) -> None:
        calls: list[tuple[int, float]] = []

        def player(path: Path, tone: int, dur: float) -> DeterrentResult:
            calls.append((tone, dur))
            return DeterrentResult(
                played=True,
                tone_hz=tone,
                duration_s=dur,
                backend="rec",
                wav_path=path,
            )

        bridge = SpeakerBridge(
            ranch_id="ranch_a", backend_name="rec", player=player
        )
        result = bridge.handle_message(
            "skyherd/ranch_a/deterrent/play",
            {"tone_hz": 14000, "duration_s": 5.0},
        )
        assert result is not None
        assert result.played is True
        assert calls == [(14000, 5.0)]

    def test_wrong_ranch_topic_returns_none(self) -> None:
        captured: list[Any] = []

        def player(path: Path, tone: int, dur: float) -> DeterrentResult:
            captured.append((tone, dur))
            return DeterrentResult(
                played=True,
                tone_hz=tone,
                duration_s=dur,
                backend="rec",
                wav_path=path,
            )

        bridge = SpeakerBridge(
            ranch_id="ranch_a", backend_name="rec", player=player
        )
        result = bridge.handle_message(
            "skyherd/ranch_z/deterrent/play",
            {"tone_hz": 14000, "duration_s": 5.0},
        )
        assert result is None
        assert captured == []

    def test_non_deterrent_topic_returns_none(self) -> None:
        bridge = SpeakerBridge(ranch_id="ranch_a", backend_name="nop")
        result = bridge.handle_message(
            "skyherd/ranch_a/thermal/coyote_cam",
            {"tone_hz": 14000, "duration_s": 5.0},
        )
        assert result is None

    def test_defaults_when_payload_missing_fields(self) -> None:
        calls: list[tuple[int, float]] = []

        def player(path: Path, tone: int, dur: float) -> DeterrentResult:
            calls.append((tone, dur))
            return DeterrentResult(
                played=True,
                tone_hz=tone,
                duration_s=dur,
                backend="rec",
                wav_path=path,
            )

        bridge = SpeakerBridge(
            ranch_id="ranch_a", backend_name="rec", player=player
        )
        bridge.handle_message("skyherd/ranch_a/deterrent/play", {})
        assert calls == [(12000, 6.0)]  # defaults


# ---------------------------------------------------------------------------
# Fixture regeneration determinism
# ---------------------------------------------------------------------------


class TestWavFixtureRegeneration:
    def test_wav_exists_in_bundle(self) -> None:
        assert DEFAULT_WAV_FIXTURE.exists()
        assert DEFAULT_WAV_FIXTURE.suffix == ".wav"

    def test_generate_is_byte_identical(self, tmp_path: Path) -> None:
        a = tmp_path / "a.wav"
        b = tmp_path / "b.wav"
        wav_generator.generate(a, tone_hz=12000, duration_s=1.0)
        wav_generator.generate(b, tone_hz=12000, duration_s=1.0)
        assert a.read_bytes() == b.read_bytes()

    def test_different_frequencies_differ(self, tmp_path: Path) -> None:
        a = tmp_path / "a.wav"
        b = tmp_path / "b.wav"
        wav_generator.generate(a, tone_hz=12000, duration_s=0.5)
        wav_generator.generate(b, tone_hz=14000, duration_s=0.5)
        assert a.read_bytes() != b.read_bytes()


# ---------------------------------------------------------------------------
# Module import is wall-clock-free
# ---------------------------------------------------------------------------


class TestNoWallClockOnImport:
    def test_reimport_does_not_call_time_time(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """speaker_bridge must not call ``time.time`` at module import."""
        import time as time_mod

        called = {"count": 0}
        real_time = time_mod.time

        def _wrapped() -> float:
            called["count"] += 1
            return real_time()

        monkeypatch.setattr(time_mod, "time", _wrapped)
        monkeypatch.delitem(sys.modules, "skyherd.edge.speaker_bridge", raising=False)
        importlib.import_module("skyherd.edge.speaker_bridge")
        assert called["count"] == 0


# ---------------------------------------------------------------------------
# run() loop best-effort
# ---------------------------------------------------------------------------


class TestRunLoopBestEffort:
    def test_run_exits_when_aiomqtt_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import aiomqtt  # type: ignore[import-untyped]

        class _Broken:
            def __init__(self, *a: Any, **kw: Any) -> None:
                raise ConnectionRefusedError("broker offline")

            async def __aenter__(self) -> Any:  # pragma: no cover
                return self

            async def __aexit__(self, *a: Any) -> None:  # pragma: no cover
                return None

        monkeypatch.setattr(aiomqtt, "Client", _Broken)
        bridge = SpeakerBridge(ranch_id="ranch_a", backend_name="nop")
        asyncio.run(asyncio.wait_for(bridge.run(), timeout=1.0))

    def test_run_processes_single_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import aiomqtt  # type: ignore[import-untyped]

        calls: list[tuple[int, float]] = []

        def player(path: Path, tone: int, dur: float) -> DeterrentResult:
            calls.append((tone, dur))
            return DeterrentResult(
                played=True,
                tone_hz=tone,
                duration_s=dur,
                backend="rec",
                wav_path=path,
            )

        class _FakeMessage:
            def __init__(self, topic: str, payload: bytes) -> None:
                self.topic = topic
                self.payload = payload

        class _FakeClient:
            def __init__(self, *a: Any, **kw: Any) -> None:
                self._queue = [
                    _FakeMessage(
                        "skyherd/ranch_a/deterrent/play",
                        json.dumps({"tone_hz": 14000, "duration_s": 0.01}).encode(),
                    )
                ]

            async def __aenter__(self) -> Any:
                return self

            async def __aexit__(self, *a: Any) -> None:
                return None

            async def subscribe(self, topic: str) -> None:
                return None

            @property
            def messages(self):  # type: ignore[no-untyped-def]
                async def _gen():
                    for msg in self._queue:
                        yield msg

                return _gen()

        monkeypatch.setattr(aiomqtt, "Client", _FakeClient)
        bridge = SpeakerBridge(
            ranch_id="ranch_a", backend_name="rec", player=player
        )
        asyncio.run(asyncio.wait_for(bridge.run(), timeout=2.0))
        assert calls == [(14000, 0.01)]

    def test_run_ignores_bad_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import aiomqtt  # type: ignore[import-untyped]

        calls: list[int] = []

        def player(path: Path, tone: int, dur: float) -> DeterrentResult:
            calls.append(tone)
            return DeterrentResult(
                played=True,
                tone_hz=tone,
                duration_s=dur,
                backend="rec",
                wav_path=path,
            )

        class _FakeMessage:
            def __init__(self, topic: str, payload: bytes) -> None:
                self.topic = topic
                self.payload = payload

        class _FakeClient:
            def __init__(self, *a: Any, **kw: Any) -> None:
                self._queue = [
                    _FakeMessage("skyherd/ranch_a/deterrent/play", b"{not-json"),
                    _FakeMessage(
                        "skyherd/ranch_a/deterrent/play",
                        json.dumps({"tone_hz": 11000, "duration_s": 0.01}).encode(),
                    ),
                ]

            async def __aenter__(self) -> Any:
                return self

            async def __aexit__(self, *a: Any) -> None:
                return None

            async def subscribe(self, topic: str) -> None:
                return None

            @property
            def messages(self):  # type: ignore[no-untyped-def]
                async def _gen():
                    for msg in self._queue:
                        yield msg

                return _gen()

        monkeypatch.setattr(aiomqtt, "Client", _FakeClient)
        bridge = SpeakerBridge(
            ranch_id="ranch_a", backend_name="rec", player=player
        )
        asyncio.run(asyncio.wait_for(bridge.run(), timeout=2.0))
        assert calls == [11000]

    def test_stop_clears_running_flag(self) -> None:
        bridge = SpeakerBridge(ranch_id="ranch_a", backend_name="nop")
        bridge.stop()
        assert bridge._running is False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class TestProperties:
    def test_topic_and_ranch_exposed(self) -> None:
        bridge = SpeakerBridge(ranch_id="ranch_b", backend_name="nop")
        assert bridge.ranch_id == "ranch_b"
        assert bridge.topic == "skyherd/ranch_b/deterrent/play"


# ---------------------------------------------------------------------------
# pygame / simpleaudio factories via fake module injection
# ---------------------------------------------------------------------------


class _FakeSound:
    played: int = 0
    stopped: int = 0

    def play(self) -> None:
        _FakeSound.played += 1

    def stop(self) -> None:
        _FakeSound.stopped += 1


class _FakePygameMixer:
    init_calls: int = 0
    sound_arg: str | None = None

    @staticmethod
    def init() -> None:
        _FakePygameMixer.init_calls += 1

    @staticmethod
    def Sound(path: str) -> _FakeSound:  # noqa: N802  (match pygame API)
        _FakePygameMixer.sound_arg = path
        return _FakeSound()


class _FakePygame:
    mixer = _FakePygameMixer


class _FakeWaveObject:
    @classmethod
    def from_wave_file(cls, path: str) -> _FakeWaveObject:
        cls.last_path = path  # type: ignore[attr-defined]
        return cls()

    def play(self) -> _FakePlayObject:
        return _FakePlayObject()


class _FakePlayObject:
    stopped: int = 0

    def stop(self) -> None:
        _FakePlayObject.stopped += 1


class _FakeSimpleaudio:
    WaveObject = _FakeWaveObject


class TestPygameFactory:
    def test_pygame_happy_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Inject fake pygame + fake time.sleep to short-circuit clamp
        monkeypatch.setitem(sys.modules, "pygame", _FakePygame)
        monkeypatch.setenv("SKYHERD_DETERRENT", "play")
        import skyherd.edge.speaker_bridge as sb

        monkeypatch.setattr(sb.time, "sleep", lambda _s: None)
        # Clear any cached backend name → rebuild
        _FakeSound.played = 0
        _FakeSound.stopped = 0
        _FakePygameMixer.init_calls = 0

        bridge = SpeakerBridge(ranch_id="ranch_a")
        assert bridge.init_backend() == "pygame"
        tmp_wav = DEFAULT_WAV_FIXTURE
        res = bridge.play(12000, 0.01)
        assert res.played is True
        assert res.backend == "pygame"
        assert res.wav_path == tmp_wav
        assert _FakePygameMixer.init_calls == 1
        assert _FakeSound.played == 1
        assert _FakeSound.stopped == 1

    def test_pygame_missing_wav(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setitem(sys.modules, "pygame", _FakePygame)
        monkeypatch.setenv("SKYHERD_DETERRENT", "play")
        bad = tmp_path / "nonexistent.wav"
        bridge = SpeakerBridge(ranch_id="ranch_a", wav_path=bad)
        res = bridge.play(12000, 0.01)
        assert res.played is False
        assert res.error is not None and "not found" in res.error

    def test_pygame_exception_returns_played_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _BrokenMixer:
            @staticmethod
            def init() -> None:
                raise RuntimeError("audio device unavailable")

            @staticmethod
            def Sound(path: str) -> _FakeSound:  # noqa: N802
                return _FakeSound()

        class _BrokenPygame:
            mixer = _BrokenMixer

        monkeypatch.setitem(sys.modules, "pygame", _BrokenPygame)
        monkeypatch.setenv("SKYHERD_DETERRENT", "play")
        bridge = SpeakerBridge(ranch_id="ranch_a")
        res = bridge.play(12000, 0.01)
        assert res.played is False
        assert res.error == "audio device unavailable"


class TestSimpleaudioFactory:
    def test_simpleaudio_happy_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Force pygame import to fail → fallback to simpleaudio
        monkeypatch.delitem(sys.modules, "pygame", raising=False)
        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "pygame":
                raise ImportError("no pygame")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        monkeypatch.setitem(sys.modules, "simpleaudio", _FakeSimpleaudio)
        monkeypatch.setenv("SKYHERD_DETERRENT", "play")
        import skyherd.edge.speaker_bridge as sb

        monkeypatch.setattr(sb.time, "sleep", lambda _s: None)

        bridge = SpeakerBridge(ranch_id="ranch_a")
        assert bridge.init_backend() == "simpleaudio"
        res = bridge.play(12000, 0.01)
        assert res.played is True
        assert res.backend == "simpleaudio"

    def test_simpleaudio_missing_wav(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.delitem(sys.modules, "pygame", raising=False)
        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "pygame":
                raise ImportError("no pygame")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        monkeypatch.setitem(sys.modules, "simpleaudio", _FakeSimpleaudio)
        monkeypatch.setenv("SKYHERD_DETERRENT", "play")
        bridge = SpeakerBridge(
            ranch_id="ranch_a", wav_path=tmp_path / "nonexistent.wav"
        )
        res = bridge.play(12000, 0.01)
        assert res.played is False
        assert res.error is not None and "not found" in res.error

    def test_simpleaudio_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _BrokenWaveObject:
            @classmethod
            def from_wave_file(cls, path: str) -> Any:
                raise OSError("decode failed")

        class _BrokenSimpleaudio:
            WaveObject = _BrokenWaveObject

        monkeypatch.delitem(sys.modules, "pygame", raising=False)
        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "pygame":
                raise ImportError("no pygame")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        monkeypatch.setitem(sys.modules, "simpleaudio", _BrokenSimpleaudio)
        monkeypatch.setenv("SKYHERD_DETERRENT", "play")

        bridge = SpeakerBridge(ranch_id="ranch_a")
        res = bridge.play(12000, 0.01)
        assert res.played is False
        assert res.error == "decode failed"


class TestResolveBackendExplicit:
    def test_explicit_pygame_without_lib_falls_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit name='pygame' with no pygame installed → nop, warning log."""
        monkeypatch.delitem(sys.modules, "pygame", raising=False)
        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name in ("pygame", "simpleaudio"):
                raise ImportError(f"no {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        monkeypatch.setenv("SKYHERD_DETERRENT", "play")
        bridge = SpeakerBridge(ranch_id="ranch_a", backend_name="pygame")
        assert bridge.init_backend() == "nop"

    def test_explicit_simpleaudio_without_lib_falls_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delitem(sys.modules, "pygame", raising=False)
        monkeypatch.delitem(sys.modules, "simpleaudio", raising=False)
        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name in ("pygame", "simpleaudio"):
                raise ImportError(f"no {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        monkeypatch.setenv("SKYHERD_DETERRENT", "play")
        bridge = SpeakerBridge(ranch_id="ranch_a", backend_name="simpleaudio")
        assert bridge.init_backend() == "nop"
