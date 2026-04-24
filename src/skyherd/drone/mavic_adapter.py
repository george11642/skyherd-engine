"""MavicAdapter — two-legged DJI + MAVSDK DroneBackend with failover.

The adapter presents the same :class:`DroneBackend` ABC as any other backend,
so call sites in :mod:`skyherd.edge.pi_to_mission`, :mod:`skyherd.mcp.drone_mcp`,
and the demo runners remain unchanged.

Internally it manages **two inner backends** and swaps between them
transparently:

``Leg A`` (primary)
    :class:`~skyherd.drone.mavic.MavicBackend` — commands the DJI Mavic
    Air 2 via the SkyHerdCompanion iOS/Android app over WebSocket (MQTT
    on Android).  DJI Mobile SDK V5 owns the radio link from the mobile
    device to the drone.

``Leg B`` (fallback)
    :class:`~skyherd.drone.pymavlink_backend.PymavlinkBackend` — talks
    MAVLink directly over USB-C OTG.  Works even when the mobile app is
    unreachable (phone battery dies, companion app crashes, MQTT broker
    disappears).

Failover flow
-------------
* At ``connect()`` time, primary is tried first with a configurable
  timeout (default 3 s).  If it fails (``DroneUnavailable``), the
  fallback is tried.  If both fail, :class:`DroneUnavailable` is raised.
* On every actuator call (``takeoff``, ``patrol``, ``return_to_home``,
  ``play_deterrent``, ``get_thermal_clip``, ``state``), the call is
  forwarded to the active leg.  If the active leg raises
  :class:`DroneError` (including :class:`DroneUnavailable`), the adapter
  records a failover and retries once on the other leg.
* A second consecutive failure raises :class:`DroneError` with both
  legs' error messages.

Determinism
-----------
All timestamps routed through an injected ``ts_provider`` (default
``time.monotonic``) so deterministic replays in tests and
``make demo SEED=42 SCENARIO=all`` stay byte-identical.

Attestation ledger
------------------
When an optional :class:`~skyherd.attest.ledger.Ledger` is supplied, the
adapter emits three event kinds:

* ``adapter.leg_selected`` — at successful connect, records which leg
  won.
* ``adapter.failover`` — on each mid-mission leg swap, records
  ``from_leg``, ``to_leg``, and ``reason``.
* ``adapter.both_legs_failed`` — terminal failure (last resort).

Mission IDs emitted on patrol/patrol_mission flow through the same
ledger chain so the replay test in Phase 7-04 can verify monotonicity
after failover.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from skyherd.drone.interface import (
    DroneBackend,
    DroneError,
    DroneState,
    DroneUnavailable,
    Waypoint,
)

logger = logging.getLogger(__name__)

__all__ = ["MavicAdapter"]

_DEFAULT_CONNECT_TIMEOUT_S = 3.0
_LEG_DJI = "dji"
_LEG_MAVSDK = "mavsdk"


class MavicAdapter(DroneBackend):
    """Two-legged drone backend with DJI → MAVSDK mid-mission failover.

    Parameters
    ----------
    primary:
        DJI-side leg.  When ``None``, a :class:`MavicBackend` is lazily
        constructed with default env vars.
    fallback:
        MAVSDK-side leg.  When ``None``, a :class:`PymavlinkBackend` is
        lazily constructed with default env vars.
    ledger:
        Optional attestation ledger.  When supplied, adapter events are
        appended to it with ``ts`` from ``ts_provider``.
    ts_provider:
        Monotonic clock for ledger timestamps.  Default
        :func:`time.monotonic`.  Tests inject a deterministic lambda.
    connect_timeout_s:
        Wall timeout for the DJI-leg connect attempt before falling
        back.  Default 3 s.
    ranch_id:
        Ranch id recorded on mission metadata and ledger entries.
    """

    def __init__(
        self,
        *,
        primary: DroneBackend | None = None,
        fallback: DroneBackend | None = None,
        ledger: Any = None,
        ts_provider: Callable[[], float] = time.monotonic,
        connect_timeout_s: float = _DEFAULT_CONNECT_TIMEOUT_S,
        ranch_id: str = "ranch_a",
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._ledger = ledger
        self._ts_provider = ts_provider
        self._connect_timeout_s = connect_timeout_s
        self._ranch_id = ranch_id

        self._active: DroneBackend | None = None
        self._active_leg: str | None = None
        self._failover_count: int = 0
        self._seq: int = 0

    # ------------------------------------------------------------------
    # Public introspection
    # ------------------------------------------------------------------

    @property
    def active_leg(self) -> str | None:
        """Return the currently active leg name (``"dji"``, ``"mavsdk"`` or ``None``)."""
        return self._active_leg

    @property
    def failover_count(self) -> int:
        """Total number of leg swaps since construction."""
        return self._failover_count

    # ------------------------------------------------------------------
    # Lazy leg construction (avoids importing heavy deps when not used)
    # ------------------------------------------------------------------

    def _get_primary(self) -> DroneBackend:
        if self._primary is None:
            from skyherd.drone.mavic import MavicBackend  # noqa: PLC0415

            self._primary = MavicBackend()
        return self._primary

    def _get_fallback(self) -> DroneBackend:
        if self._fallback is None:
            from skyherd.drone.pymavlink_backend import PymavlinkBackend  # noqa: PLC0415

            self._fallback = PymavlinkBackend()
        return self._fallback

    # ------------------------------------------------------------------
    # DroneBackend implementation
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Try DJI first, fall back to MAVSDK.

        Records ``adapter.leg_selected`` ledger event on success.
        Raises :class:`DroneUnavailable` with combined error text when
        both legs fail.
        """
        # Leg A: DJI
        primary = self._get_primary()
        dji_err: str | None = None
        try:
            await asyncio.wait_for(primary.connect(), timeout=self._connect_timeout_s)
            self._active = primary
            self._active_leg = _LEG_DJI
            self._record_event("adapter.leg_selected", {"leg": _LEG_DJI})
            logger.info("MavicAdapter: DJI leg selected")
            return
        except (DroneUnavailable, DroneError, TimeoutError, asyncio.TimeoutError) as exc:
            dji_err = str(exc)
            logger.warning("MavicAdapter: DJI leg unavailable — %s", dji_err)

        # Leg B: MAVSDK
        fallback = self._get_fallback()
        mav_err: str | None = None
        try:
            await asyncio.wait_for(fallback.connect(), timeout=self._connect_timeout_s)
            self._active = fallback
            self._active_leg = _LEG_MAVSDK
            self._record_event(
                "adapter.leg_selected",
                {"leg": _LEG_MAVSDK, "dji_error": dji_err},
            )
            logger.info("MavicAdapter: MAVSDK leg selected (DJI failed: %s)", dji_err)
            return
        except (DroneUnavailable, DroneError, TimeoutError, asyncio.TimeoutError) as exc:
            mav_err = str(exc)

        # Both failed — terminal
        self._record_event(
            "adapter.both_legs_failed",
            {"dji_error": dji_err, "mavsdk_error": mav_err},
        )
        raise DroneUnavailable(
            f"Both drone legs failed: dji={dji_err} mavsdk={mav_err}"
        )

    async def takeoff(self, alt_m: float = 30.0) -> None:
        await self._invoke("takeoff", alt_m=alt_m)

    async def patrol(self, waypoints: list[Waypoint]) -> None:
        # Phase 7-03 hook: serialize through MissionV1 when available.
        try:
            from skyherd.drone.mission_schema import (  # noqa: PLC0415
                MissionMetadata,
                MissionV1,
            )

            mission = MissionV1(
                metadata=MissionMetadata(
                    mission_id=self._next_mission_id(),
                    ranch_id=self._ranch_id,
                ),
                waypoints=list(waypoints),
            )
            await self.patrol_mission(mission)
        except ImportError:
            # Schema module not shipped yet (running against pre-07-03 tree).
            await self._invoke("patrol", waypoints=list(waypoints))

    async def patrol_mission(self, mission: Any) -> None:
        """Execute a :class:`MissionV1` with failover semantics.

        Accepts any object with a ``waypoints`` attribute + ``metadata.mission_id``
        to stay forward-compat with schema v2+.
        """
        waypoints = list(mission.waypoints)
        mission_id = getattr(getattr(mission, "metadata", None), "mission_id", None)
        await self._invoke(
            "patrol",
            waypoints=waypoints,
            _ledger_extra={"mission_id": mission_id} if mission_id else None,
        )

    async def return_to_home(self) -> None:
        await self._invoke("return_to_home")

    async def play_deterrent(self, tone_hz: int = 12000, duration_s: float = 6.0) -> None:
        await self._invoke("play_deterrent", tone_hz=tone_hz, duration_s=duration_s)

    async def get_thermal_clip(self, duration_s: float = 10.0) -> Path:
        return await self._invoke("get_thermal_clip", duration_s=duration_s)

    async def state(self) -> DroneState:
        return await self._invoke("state")

    async def disconnect(self) -> None:
        """Disconnect *both* legs — even the idle one — so sockets don't leak."""
        errors: list[str] = []
        for leg_name, leg in (
            (_LEG_DJI, self._primary),
            (_LEG_MAVSDK, self._fallback),
        ):
            if leg is None:
                continue
            try:
                await leg.disconnect()
            except (DroneError, DroneUnavailable, Exception) as exc:  # noqa: BLE001
                errors.append(f"{leg_name}: {exc}")
        self._active = None
        self._active_leg = None
        if errors:
            logger.warning("MavicAdapter: disconnect issues — %s", "; ".join(errors))

    # ------------------------------------------------------------------
    # Internal: call-with-failover helper
    # ------------------------------------------------------------------

    async def _invoke(self, method_name: str, **kwargs: Any) -> Any:
        """Invoke ``method_name`` on the active leg with one-shot failover.

        If the active leg raises :class:`DroneError` / :class:`DroneUnavailable`,
        swap legs and retry once.  A second failure raises a combined
        :class:`DroneError`.

        The private kwarg ``_ledger_extra`` (if present) is stripped
        before calling the backend and merged into the failover ledger
        entry.
        """
        if self._active is None:
            raise DroneUnavailable("MavicAdapter not connected — call connect() first")

        ledger_extra = kwargs.pop("_ledger_extra", None)

        primary_leg = self._active_leg
        try:
            method = getattr(self._active, method_name)
            return await method(**kwargs)
        except (DroneError, DroneUnavailable) as exc:
            first_err = str(exc)
            logger.warning(
                "MavicAdapter: %s on leg=%s failed — %s (failover attempt)",
                method_name,
                primary_leg,
                first_err,
            )

            other = self._swap_active_leg()
            if other is None:
                # Nothing to fall back to — terminal.
                raise

            event_data: dict[str, Any] = {
                "from_leg": primary_leg,
                "to_leg": self._active_leg,
                "method": method_name,
                "reason": first_err,
            }
            if ledger_extra:
                event_data.update(ledger_extra)
            self._record_event("adapter.failover", event_data)
            self._failover_count += 1

            try:
                method = getattr(self._active, method_name)
                return await method(**kwargs)
            except (DroneError, DroneUnavailable) as exc2:
                raise DroneError(
                    f"Both legs failed on {method_name}: "
                    f"{primary_leg}={first_err} {self._active_leg}={exc2}"
                ) from exc2

    # ------------------------------------------------------------------
    # Leg swap + ledger helpers
    # ------------------------------------------------------------------

    def _swap_active_leg(self) -> DroneBackend | None:
        """Swap to the *other* leg if it's been constructed; return it or None.

        After swap, ``self._active`` and ``self._active_leg`` reflect the new
        active leg.
        """
        if self._active_leg == _LEG_DJI and self._fallback is not None:
            self._active = self._fallback
            self._active_leg = _LEG_MAVSDK
            return self._fallback
        if self._active_leg == _LEG_MAVSDK and self._primary is not None:
            self._active = self._primary
            self._active_leg = _LEG_DJI
            return self._primary
        return None

    def _record_event(self, kind: str, data: dict[str, Any]) -> None:
        """Write an adapter event to the ledger if one is attached.

        Silent no-op when ``self._ledger is None`` — adapter still functions
        without attestation (e.g. in simple unit tests).
        """
        if self._ledger is None:
            return
        try:
            payload = {
                "ts": self._ts_provider(),
                "kind": kind,
                "ranch_id": self._ranch_id,
                **data,
            }
            self._ledger.append(kind=kind, data=payload)
        except Exception as exc:  # noqa: BLE001
            # Ledger failures must never crash the drone path — log and move on.
            logger.error("MavicAdapter: ledger append failed: %s", exc)

    def _next_mission_id(self) -> str:
        """Deterministic, monotonic mission id.

        Format: ``mission_<8-hex-zero-padded>``.  Counter is per-instance;
        ``MavicAdapter`` is typically a singleton per demo run so ids are
        stable for the duration.
        """
        self._seq += 1
        return f"mission_{self._seq:08x}"
