"""SpeakerBridge — ground-side acoustic deterrent playback.

Subscribes to ``skyherd/{ranch}/deterrent/play`` MQTT events (emitted by
:class:`~skyherd.edge.pi_to_mission.PiToMissionBridge` when the
FenceLineDispatcher fires ``play_deterrent``) and plays a bundled predator
deterrent WAV to the OS audio device.

Design
------
* **No new runtime deps.**  Audio libraries (``pygame``, ``simpleaudio``) are
  imported behind ``try/except ImportError``.  The module is import-safe in
  headless CI with zero audio libraries installed.
* **Mute by default in CI.**  ``SKYHERD_DETERRENT=mute`` (or ``"false"`` /
  ``"0"``) forces the no-op backend regardless of available audio libs.
* **Deterministic.**  No wall-clock imports at module scope.  Timestamps flow
  through an injected ``clock`` callable for tests.
* **Failure-tolerant.**  Exceptions in the playback backend return a
  :class:`DeterrentResult` with ``played=False`` and an error string — never
  propagate to the MQTT subscriber loop.

Test hooks
----------
* ``player`` — DI override for the low-level playback callable.
* ``backend_name`` — force a specific backend (``"pygame"`` / ``"simpleaudio"`` /
  ``"nop"``) without import-dance.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_WAV_FIXTURE",
    "DeterrentResult",
    "SpeakerBridge",
    "nop_player",
]

_DEFAULT_RANCH_ID = "ranch_a"
_DEFAULT_MQTT_URL = "mqtt://localhost:1883"
_DEFAULT_TOPIC_SUFFIX = "/deterrent/play"

# Max time we'll actually sleep during a play() call — prevents a malicious
# or mistyped duration_s from stalling the subscriber loop for minutes.
_MAX_PLAYBACK_S = 10.0

DEFAULT_WAV_FIXTURE = (
    Path(__file__).parent / "fixtures" / "deterrent" / "predator_12khz.wav"
)


# ---------------------------------------------------------------------------
# DeterrentResult
# ---------------------------------------------------------------------------


@dataclass
class DeterrentResult:
    """Outcome of one deterrent ``play()`` call."""

    played: bool
    tone_hz: int
    duration_s: float
    backend: str
    wav_path: Path | None
    error: str | None = None


PlayerFn = Callable[[Path, int, float], DeterrentResult]


def nop_player(wav_path: Path, tone_hz: int, duration_s: float) -> DeterrentResult:
    """Default no-op player — logs and returns played=False."""
    logger.info(
        "SpeakerBridge: deterrent NOP (tone_hz=%d duration_s=%.1f path=%s)",
        tone_hz,
        duration_s,
        wav_path,
    )
    return DeterrentResult(
        played=False,
        tone_hz=tone_hz,
        duration_s=duration_s,
        backend="nop",
        wav_path=wav_path,
    )


# ---------------------------------------------------------------------------
# Backend resolution
# ---------------------------------------------------------------------------


_MUTE_SENTINELS = frozenset({"mute", "false", "0", "off", ""})


def _env_is_muted() -> bool:
    raw = os.environ.get("SKYHERD_DETERRENT", "mute").strip().lower()
    # Default is mute (safe for headless CI).  Set SKYHERD_DETERRENT=play to
    # enable real audio.
    return raw in _MUTE_SENTINELS


def _resolve_backend(name: str | None) -> tuple[str, PlayerFn]:
    """Pick a backend + player function.

    Order of preference:
    1. Explicit ``name`` argument.
    2. ``SKYHERD_DETERRENT`` env var — ``mute`` / ``false`` / ``0`` → ``nop``.
    3. ``pygame.mixer`` if available.
    4. ``simpleaudio`` if available.
    5. ``nop`` fallback + single INFO log line.
    """
    if name == "nop":
        return "nop", nop_player
    if name is None and _env_is_muted():
        return "nop", nop_player

    if name in (None, "pygame"):
        try:
            player = _pygame_player_factory()
            return "pygame", player
        except ImportError:
            if name == "pygame":
                logger.warning(
                    "SpeakerBridge: pygame requested but not installed; falling back to nop"
                )

    if name in (None, "simpleaudio"):
        try:
            player = _simpleaudio_player_factory()
            return "simpleaudio", player
        except ImportError:
            if name == "simpleaudio":
                logger.warning(
                    "SpeakerBridge: simpleaudio requested but not installed; falling back to nop"
                )

    logger.info(
        "SpeakerBridge: no audio backend available (pygame/simpleaudio missing); using nop"
    )
    return "nop", nop_player


def _pygame_player_factory() -> PlayerFn:
    import pygame  # type: ignore[import-untyped]  # noqa: PLC0415

    def player(wav_path: Path, tone_hz: int, duration_s: float) -> DeterrentResult:
        try:
            if not wav_path.exists():
                return DeterrentResult(
                    played=False,
                    tone_hz=tone_hz,
                    duration_s=duration_s,
                    backend="pygame",
                    wav_path=wav_path,
                    error=f"wav fixture not found: {wav_path}",
                )
            pygame.mixer.init()
            sound = pygame.mixer.Sound(str(wav_path))
            sound.play()
            clamped = min(duration_s, _MAX_PLAYBACK_S)
            time.sleep(clamped)
            sound.stop()
            return DeterrentResult(
                played=True,
                tone_hz=tone_hz,
                duration_s=duration_s,
                backend="pygame",
                wav_path=wav_path,
            )
        except Exception as exc:  # noqa: BLE001
            return DeterrentResult(
                played=False,
                tone_hz=tone_hz,
                duration_s=duration_s,
                backend="pygame",
                wav_path=wav_path,
                error=str(exc),
            )

    return player


def _simpleaudio_player_factory() -> PlayerFn:
    import simpleaudio  # type: ignore[import-untyped]  # noqa: PLC0415

    def player(wav_path: Path, tone_hz: int, duration_s: float) -> DeterrentResult:
        try:
            if not wav_path.exists():
                return DeterrentResult(
                    played=False,
                    tone_hz=tone_hz,
                    duration_s=duration_s,
                    backend="simpleaudio",
                    wav_path=wav_path,
                    error=f"wav fixture not found: {wav_path}",
                )
            wave_obj = simpleaudio.WaveObject.from_wave_file(str(wav_path))
            play_obj = wave_obj.play()
            clamped = min(duration_s, _MAX_PLAYBACK_S)
            time.sleep(clamped)
            play_obj.stop()
            return DeterrentResult(
                played=True,
                tone_hz=tone_hz,
                duration_s=duration_s,
                backend="simpleaudio",
                wav_path=wav_path,
            )
        except Exception as exc:  # noqa: BLE001
            return DeterrentResult(
                played=False,
                tone_hz=tone_hz,
                duration_s=duration_s,
                backend="simpleaudio",
                wav_path=wav_path,
                error=str(exc),
            )

    return player


# ---------------------------------------------------------------------------
# SpeakerBridge
# ---------------------------------------------------------------------------


class SpeakerBridge:
    """Subscribe to deterrent MQTT events + play WAV to OS audio.

    Parameters
    ----------
    ranch_id:
        Target ranch id; used in the topic subscription pattern.
    mqtt_url:
        Full broker URL; defaults to ``MQTT_URL`` env or ``mqtt://localhost:1883``.
    wav_path:
        Override the bundled predator deterrent WAV fixture.
    backend_name:
        Force a specific playback backend (test / CI mode).
    player:
        DI override — a callable ``(wav_path, tone_hz, duration_s) -> DeterrentResult``.
    clock:
        Injectable wall-clock source for tests (default :func:`time.time`).
    """

    def __init__(
        self,
        *,
        ranch_id: str | None = None,
        mqtt_url: str | None = None,
        wav_path: Path | None = None,
        backend_name: str | None = None,
        player: PlayerFn | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._ranch_id = ranch_id or os.environ.get("RANCH_ID", _DEFAULT_RANCH_ID)
        self._mqtt_url = mqtt_url or os.environ.get("MQTT_URL", _DEFAULT_MQTT_URL)
        self._wav_path = wav_path or DEFAULT_WAV_FIXTURE
        self._clock = clock or time.time
        self._explicit_backend_name = backend_name
        self._explicit_player = player
        self._backend_name: str | None = None
        self._player: PlayerFn | None = None
        self._running = False
        self._topic = f"skyherd/{self._ranch_id}{_DEFAULT_TOPIC_SUFFIX}"

    # ------------------------------------------------------------------
    # Public: backend init + play
    # ------------------------------------------------------------------

    def init_backend(self) -> str:
        """Resolve + cache the playback backend.  Idempotent."""
        if self._player is not None and self._backend_name is not None:
            return self._backend_name
        if self._explicit_player is not None:
            self._player = self._explicit_player
            self._backend_name = self._explicit_backend_name or "injected"
            return self._backend_name
        self._backend_name, self._player = _resolve_backend(self._explicit_backend_name)
        return self._backend_name

    def play(self, tone_hz: int, duration_s: float) -> DeterrentResult:
        """Play the deterrent.  Returns a :class:`DeterrentResult`."""
        self.init_backend()
        assert self._player is not None  # noqa: S101  (init_backend always sets)
        return self._player(self._wav_path, int(tone_hz), float(duration_s))

    @property
    def backend_name(self) -> str | None:
        return self._backend_name

    @property
    def topic(self) -> str:
        return self._topic

    @property
    def ranch_id(self) -> str:
        return self._ranch_id

    # ------------------------------------------------------------------
    # Message handling (test-friendly, directly callable)
    # ------------------------------------------------------------------

    def handle_message(self, topic: str, payload: dict[str, Any]) -> DeterrentResult | None:
        """Process one deterrent MQTT event.  Returns ``None`` if topic mismatches."""
        if topic != self._topic:
            logger.debug("SpeakerBridge drop: topic %s != %s", topic, self._topic)
            return None
        tone_hz = int(payload.get("tone_hz", 12000))
        duration_s = float(payload.get("duration_s", 6.0))
        return self.play(tone_hz, duration_s)

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Subscribe to the deterrent topic and play events as they arrive."""
        self._running = True
        self._install_signal_handlers()
        self.init_backend()
        logger.info(
            "SpeakerBridge started — ranch=%s topic=%s backend=%s wav=%s",
            self._ranch_id,
            self._topic,
            self._backend_name,
            self._wav_path,
        )
        try:
            import aiomqtt  # type: ignore[import-untyped]  # noqa: PLC0415
        except ImportError:
            logger.warning("aiomqtt unavailable; SpeakerBridge.run() exiting")
            return

        host, _, port_str = self._mqtt_url.split("://", 1)[-1].rpartition(":")
        try:
            port = int(port_str)
        except ValueError:
            port = 1883
        host = host or "localhost"

        try:
            async with aiomqtt.Client(hostname=host, port=port) as client:
                await client.subscribe(self._topic)
                async for message in client.messages:
                    if not self._running:
                        break
                    try:
                        payload = json.loads(message.payload)
                    except (TypeError, ValueError) as exc:
                        logger.debug(
                            "SpeakerBridge bad JSON on %s: %s", message.topic, exc
                        )
                        continue
                    topic = str(message.topic)
                    # Run the blocking player in the default executor so the
                    # subscriber doesn't stall on audio playback.
                    loop = asyncio.get_running_loop()
                    try:
                        await loop.run_in_executor(
                            None, self.handle_message, topic, payload
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.error("SpeakerBridge handle_message error: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SpeakerBridge.run() exiting: %s", exc)

    def stop(self) -> None:
        """Request graceful shutdown."""
        self._running = False

    def _install_signal_handlers(self) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGINT, self.stop)
            loop.add_signal_handler(signal.SIGTERM, self.stop)
        except (NotImplementedError, RuntimeError) as exc:
            logger.debug("signal handler unavailable: %s", exc)


# Awaitable alias for external callers who prefer an async publish hook
PublishFn = Callable[[str, bytes], Awaitable[None]]
