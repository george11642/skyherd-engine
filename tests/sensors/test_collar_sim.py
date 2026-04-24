"""Tests for ``src/skyherd/sensors/collar_sim.py``.

Determinism is the headline requirement: same seed → byte-identical output.
"""

from __future__ import annotations

import json
import math

import pytest

from skyherd.sensors.collar_sim import CollarSimEmitter, run_async


def _make(seed: int = 42, **kwargs: object) -> CollarSimEmitter:
    return CollarSimEmitter(
        ranch_id="ranch_a",
        cow_tag="A001",
        seed=seed,
        **kwargs,  # type: ignore[arg-type]
    )


class TestEmitterSchema:
    def test_payload_has_sim_schema_keys(self) -> None:
        emitter = _make()
        payload = emitter.tick()
        required = {
            "ts",
            "kind",
            "ranch",
            "entity",
            "pos",
            "heading_deg",
            "activity",
            "battery_pct",
        }
        assert required.issubset(payload.keys())
        assert payload["kind"] == "collar.reading"
        assert payload["ranch"] == "ranch_a"
        assert payload["entity"] == "A001"

    def test_payload_is_json_serialisable(self) -> None:
        emitter = _make()
        payload = emitter.tick()
        # Must be round-trippable through JSON; no tuples, no NaN.
        json.loads(json.dumps(payload, allow_nan=False))

    def test_topic_format(self) -> None:
        emitter = _make()
        assert emitter.topic == "skyherd/ranch_a/collar/A001"


class TestEmitterActivity:
    def test_activity_always_in_valid_set(self) -> None:
        emitter = _make()
        seen = set()
        for _ in range(200):
            seen.add(emitter.tick()["activity"])
        assert seen.issubset({"resting", "grazing", "walking"})
        # Over 200 ticks, we should see at least two different states
        assert len(seen) >= 2


class TestEmitterBattery:
    def test_battery_drains_monotonically(self) -> None:
        emitter = _make(drain_rate_per_tick=1.0, initial_battery_pct=100.0)
        prev = 100.0
        for _ in range(50):
            bp = emitter.tick()["battery_pct"]
            assert isinstance(bp, (int, float))
            assert bp <= prev + 1e-9
            prev = float(bp)

    def test_battery_clamped_at_zero(self) -> None:
        emitter = _make(drain_rate_per_tick=10.0, initial_battery_pct=5.0)
        # After many ticks, battery can't go negative.
        for _ in range(50):
            bp = emitter.tick()["battery_pct"]
        assert bp == 0.0

    def test_initial_battery_clamped_on_construction(self) -> None:
        emitter = _make(initial_battery_pct=150.0)
        first = float(emitter.tick()["battery_pct"])  # type: ignore[arg-type]
        assert first <= 100.0


class TestEmitterPosition:
    def test_position_drifts_bounded(self) -> None:
        emitter = _make(start_pos=(34.0, -106.0))
        max_dist_deg = 0.0
        for _ in range(1000):
            pos = emitter.tick()["pos"]
            assert isinstance(pos, list) and len(pos) == 2
            dist = math.hypot(pos[0] - 34.0, pos[1] - (-106.0))  # type: ignore[operator]
            max_dist_deg = max(max_dist_deg, dist)
        # 1000 steps of sigma ~2e-5 * 2.5 (walking) should stay well under 0.5° (~50 km).
        assert max_dist_deg < 0.5

    def test_heading_updates_on_movement(self) -> None:
        emitter = _make()
        headings = {float(emitter.tick()["heading_deg"]) for _ in range(50)}  # type: ignore[arg-type]
        # With random walk, heading should vary (not pinned at 0).
        assert len(headings) > 1


class TestEmitterHeartRate:
    def test_heart_rate_in_physiological_range(self) -> None:
        emitter = _make()
        for _ in range(500):
            hr = float(emitter.tick()["heart_rate_bpm"])  # type: ignore[arg-type]
            assert 30.0 <= hr <= 100.0


class TestEmitterDeterminism:
    def test_same_seed_same_output(self) -> None:
        a = _make(seed=42)
        b = _make(seed=42)
        payloads_a = [json.dumps(a.tick(), sort_keys=True) for _ in range(100)]
        payloads_b = [json.dumps(b.tick(), sort_keys=True) for _ in range(100)]
        assert payloads_a == payloads_b

    def test_different_seeds_different_output(self) -> None:
        a = _make(seed=42)
        b = _make(seed=43)
        payloads_a = [json.dumps(a.tick(), sort_keys=True) for _ in range(50)]
        payloads_b = [json.dumps(b.tick(), sort_keys=True) for _ in range(50)]
        # With a different seed, payloads should differ at least somewhere.
        assert payloads_a != payloads_b

    def test_ts_provider_is_used_when_set(self) -> None:
        counter = [100.0]

        def ts() -> float:
            counter[0] += 7.0
            return counter[0]

        emitter = _make(ts_provider=ts)
        p1 = emitter.tick()
        p2 = emitter.tick()
        assert p1["ts"] == 107.0
        assert p2["ts"] == 114.0

    def test_default_ts_is_monotonic_tick_counter(self) -> None:
        emitter = _make()
        ticks = [float(emitter.tick()["ts"]) for _ in range(5)]  # type: ignore[arg-type]
        assert ticks == [1.0, 2.0, 3.0, 4.0, 5.0]


# ----------------------------------------------------------------------
# run_async
# ----------------------------------------------------------------------


class _RecordingPublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def __call__(self, topic: str, payload: dict[str, object]) -> None:
        self.calls.append((topic, payload))


class TestRunAsync:
    @pytest.mark.asyncio
    async def test_publishes_n_messages(self) -> None:
        emitter = _make()
        pub = _RecordingPublisher()

        emitted = await run_async(emitter, pub, count=5)

        assert len(emitted) == 5
        assert len(pub.calls) == 5
        assert all(topic == "skyherd/ranch_a/collar/A001" for topic, _ in pub.calls)

    @pytest.mark.asyncio
    async def test_run_async_preserves_determinism(self) -> None:
        pub_a = _RecordingPublisher()
        pub_b = _RecordingPublisher()
        await run_async(_make(seed=7), pub_a, count=30)
        await run_async(_make(seed=7), pub_b, count=30)

        payloads_a = [json.dumps(p, sort_keys=True) for _t, p in pub_a.calls]
        payloads_b = [json.dumps(p, sort_keys=True) for _t, p in pub_b.calls]
        assert payloads_a == payloads_b

    @pytest.mark.asyncio
    async def test_run_async_zero_count_is_noop(self) -> None:
        pub = _RecordingPublisher()
        emitted = await run_async(_make(), pub, count=0)
        assert emitted == []
        assert pub.calls == []
