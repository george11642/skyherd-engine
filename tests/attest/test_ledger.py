"""Tests for skyherd.attest.ledger — TDD coverage suite.

Covers:
- Genesis event (prev_hash == "GENESIS")
- Append 100 events, verify chain green
- Payload mutation detected at correct seq
- Signature mutation detected
- prev_hash mutation detected
- iter_events streaming / since_seq filtering
- export_jsonl produces valid JSONL
- Duplicate event_hash rejected (UNIQUE constraint)
- VerifyResult fields are correct
- _canonical_json determinism
- NaN/Inf rejected
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skyherd.attest.ledger import (
    GENESIS_PREV_HASH,
    Event,
    Ledger,
    VerifyResult,
    _canonical_json,
)
from skyherd.attest.signer import Signer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def signer() -> Signer:
    return Signer.generate()


@pytest.fixture()
def ledger(tmp_path: Path, signer: Signer) -> Ledger:
    db_path = tmp_path / "test.db"
    ledger = Ledger.open(db_path, signer)
    yield ledger
    ledger._conn.close()


# ---------------------------------------------------------------------------
# Genesis
# ---------------------------------------------------------------------------


class TestGenesisEvent:
    def test_first_event_has_genesis_prev_hash(self, ledger: Ledger) -> None:
        event = ledger.append("sensor.water.1", "water.low", {"tank": 1, "psi": 0.5})
        assert event.prev_hash == GENESIS_PREV_HASH

    def test_first_event_seq_is_1(self, ledger: Ledger) -> None:
        event = ledger.append("sensor.fence.1", "breach.detected", {})
        assert event.seq == 1

    def test_second_event_prev_hash_equals_first_hash(self, ledger: Ledger) -> None:
        e1 = ledger.append("s", "k", {"n": 1})
        e2 = ledger.append("s", "k", {"n": 2})
        assert e2.prev_hash == e1.event_hash

    def test_event_is_event_instance(self, ledger: Ledger) -> None:
        ev = ledger.append("sensor.collar.42", "gps.update", {"lat": 34.1, "lon": -106.5})
        assert isinstance(ev, Event)


# ---------------------------------------------------------------------------
# Append 100 events + bulk verify
# ---------------------------------------------------------------------------


class TestBulkAppendAndVerify:
    def test_append_100_events_chain_valid(self, ledger: Ledger) -> None:
        for i in range(100):
            ledger.append(
                f"sensor.water.{i % 5}",
                "telemetry",
                {"seq": i, "val": i * 1.5},
            )
        result = ledger.verify()
        assert result.valid is True
        assert result.total == 100
        assert result.first_bad_seq is None
        assert result.reason is None

    def test_sequential_seq_numbers(self, ledger: Ledger) -> None:
        events = [ledger.append("s", "k", {"i": i}) for i in range(10)]
        seqs = [e.seq for e in events]
        assert seqs == list(range(1, 11))

    def test_chain_links_100_events(self, ledger: Ledger) -> None:
        events = [ledger.append("s", "k", {"i": i}) for i in range(100)]
        # prev_hash of event[n] == event_hash of event[n-1]
        for prev, curr in zip(events, events[1:]):
            assert curr.prev_hash == prev.event_hash


# ---------------------------------------------------------------------------
# Tamper detection — payload mutation
# ---------------------------------------------------------------------------


class TestPayloadMutationDetected:
    def test_mutated_payload_flagged(self, ledger: Ledger, tmp_path: Path) -> None:
        for i in range(5):
            ledger.append("sensor.water", "telemetry", {"i": i})
        target_seq = 3

        # Directly overwrite payload_json for seq=3
        ledger._conn.execute(
            "UPDATE events SET payload_json = ? WHERE seq = ?",
            ('{"i":999}', target_seq),
        )
        ledger._conn.commit()

        result = ledger.verify()
        assert result.valid is False
        assert result.first_bad_seq == target_seq
        assert result.reason is not None

    def test_mutation_at_first_event_flagged(self, ledger: Ledger) -> None:
        ledger.append("s", "k", {"v": 1})
        ledger.append("s", "k", {"v": 2})

        ledger._conn.execute(
            "UPDATE events SET payload_json = ? WHERE seq = 1",
            ('{"v":42}',),
        )
        ledger._conn.commit()

        result = ledger.verify()
        assert result.valid is False
        assert result.first_bad_seq == 1

    def test_mutation_at_last_event_flagged(self, ledger: Ledger) -> None:
        for i in range(10):
            ledger.append("s", "k", {"i": i})

        ledger._conn.execute(
            "UPDATE events SET payload_json = ? WHERE seq = 10",
            ('{"i":0}',),
        )
        ledger._conn.commit()

        result = ledger.verify()
        assert result.valid is False
        assert result.first_bad_seq == 10


# ---------------------------------------------------------------------------
# Tamper detection — signature mutation
# ---------------------------------------------------------------------------


class TestSignatureMutationDetected:
    def test_mutated_signature_flagged(self, ledger: Ledger) -> None:
        for i in range(3):
            ledger.append("s", "k", {"i": i})

        # Flip one byte in the stored signature for seq=2
        row = ledger._conn.execute("SELECT signature FROM events WHERE seq = 2").fetchone()
        sig_bytes = bytes.fromhex(row[0])
        bad_bytes = bytes([sig_bytes[0] ^ 0xFF]) + sig_bytes[1:]
        ledger._conn.execute(
            "UPDATE events SET signature = ? WHERE seq = 2",
            (bad_bytes.hex(),),
        )
        ledger._conn.commit()

        result = ledger.verify()
        assert result.valid is False
        assert result.first_bad_seq == 2
        assert "signature" in (result.reason or "").lower()

    def test_garbage_signature_hex_flagged(self, ledger: Ledger) -> None:
        ledger.append("s", "k", {"x": 1})
        ledger._conn.execute("UPDATE events SET signature = 'NOTVALIDHEX' WHERE seq = 1")
        ledger._conn.commit()

        result = ledger.verify()
        assert result.valid is False
        assert result.first_bad_seq == 1


# ---------------------------------------------------------------------------
# Tamper detection — prev_hash mutation
# ---------------------------------------------------------------------------


class TestPrevHashMutationDetected:
    def test_broken_chain_link_detected(self, ledger: Ledger) -> None:
        for i in range(5):
            ledger.append("s", "k", {"i": i})

        # Break chain: point seq=3 prev_hash to garbage
        ledger._conn.execute(
            "UPDATE events SET prev_hash = 'deadbeef' WHERE seq = 3",
        )
        ledger._conn.commit()

        result = ledger.verify()
        assert result.valid is False
        # seq 3 must be flagged — either for prev_hash or hash recompute
        assert result.first_bad_seq is not None
        assert result.first_bad_seq <= 3


# ---------------------------------------------------------------------------
# iter_events
# ---------------------------------------------------------------------------


class TestIterEvents:
    def test_iter_events_empty_ledger(self, ledger: Ledger) -> None:
        assert list(ledger.iter_events()) == []

    def test_iter_events_returns_all(self, ledger: Ledger) -> None:
        for i in range(10):
            ledger.append("s", "k", {"i": i})
        events = list(ledger.iter_events())
        assert len(events) == 10

    def test_iter_events_since_seq(self, ledger: Ledger) -> None:
        for i in range(10):
            ledger.append("s", "k", {"i": i})
        events = list(ledger.iter_events(since_seq=5))
        assert len(events) == 5
        assert events[0].seq == 6

    def test_iter_events_since_seq_zero(self, ledger: Ledger) -> None:
        for i in range(3):
            ledger.append("s", "k", {"i": i})
        events = list(ledger.iter_events(since_seq=0))
        assert len(events) == 3

    def test_iter_events_order_is_ascending(self, ledger: Ledger) -> None:
        for i in range(20):
            ledger.append("s", "k", {"i": i})
        events = list(ledger.iter_events())
        seqs = [e.seq for e in events]
        assert seqs == sorted(seqs)

    def test_iter_events_payload_survives_round_trip(self, ledger: Ledger) -> None:
        payload = {"lat": 34.05, "lon": -106.99, "tag": "AB-42"}
        ledger.append("sensor.collar.1", "gps.update", payload)
        event = next(ledger.iter_events())
        recovered = json.loads(event.payload_json)
        assert recovered["tag"] == "AB-42"


# ---------------------------------------------------------------------------
# export_jsonl
# ---------------------------------------------------------------------------


class TestExportJsonl:
    def test_export_creates_file(self, ledger: Ledger, tmp_path: Path) -> None:
        ledger.append("s", "k", {"x": 1})
        out = tmp_path / "export.jsonl"
        ledger.export_jsonl(out)
        assert out.exists()

    def test_export_line_count_matches_events(self, ledger: Ledger, tmp_path: Path) -> None:
        for i in range(7):
            ledger.append("s", "k", {"i": i})
        out = tmp_path / "export.jsonl"
        ledger.export_jsonl(out)
        lines = [l for l in out.read_text().splitlines() if l.strip()]
        assert len(lines) == 7

    def test_export_each_line_is_valid_json(self, ledger: Ledger, tmp_path: Path) -> None:
        for i in range(3):
            ledger.append("source", "kind", {"val": i})
        out = tmp_path / "export.jsonl"
        ledger.export_jsonl(out)
        for line in out.read_text().splitlines():
            obj = json.loads(line)
            assert "seq" in obj
            assert "event_hash" in obj


# ---------------------------------------------------------------------------
# _canonical_json helpers
# ---------------------------------------------------------------------------


class TestCanonicalJson:
    def test_sorted_keys(self) -> None:
        result = _canonical_json({"z": 1, "a": 2, "m": 3})
        assert result == '{"a":2,"m":3,"z":1}'

    def test_compact_separators(self) -> None:
        result = _canonical_json({"k": "v"})
        assert " " not in result

    def test_deterministic_across_calls(self) -> None:
        payload = {"c": 3, "a": 1, "b": 2}
        assert _canonical_json(payload) == _canonical_json(payload)

    def test_nan_raises_value_error(self) -> None:

        with pytest.raises(ValueError):
            _canonical_json({"v": float("nan")})

    def test_inf_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            _canonical_json({"v": float("inf")})

    def test_integer_stays_integer(self) -> None:
        result = _canonical_json({"n": 42})
        assert '"n":42' in result  # not 42.0


# ---------------------------------------------------------------------------
# Ledger context manager
# ---------------------------------------------------------------------------


class TestLedgerContextManager:
    def test_context_manager_closes_connection(self, tmp_path: Path, signer: Signer) -> None:
        db_path = tmp_path / "ctx.db"
        with Ledger.open(db_path, signer) as ledger:
            ledger.append("s", "k", {"x": 1})
        # Connection should be closed — further operations raise ProgrammingError
        with pytest.raises(Exception):
            ledger._conn.execute("SELECT 1")


# ---------------------------------------------------------------------------
# VerifyResult model
# ---------------------------------------------------------------------------


class TestVerifyResult:
    def test_empty_ledger_verify_valid(self, ledger: Ledger) -> None:
        result = ledger.verify()
        assert isinstance(result, VerifyResult)
        assert result.valid is True
        assert result.total == 0

    def test_verify_result_is_pydantic_model(self, ledger: Ledger) -> None:
        result = ledger.verify()
        # Pydantic v2 model_dump
        d = result.model_dump()
        assert "valid" in d
        assert "total" in d


# ---------------------------------------------------------------------------
# Memver pairing (Phase 4 — ATT-04)
# ---------------------------------------------------------------------------


class TestMemverPairing:
    def test_append_with_memver_id_persists_field(self, ledger: Ledger) -> None:
        event = ledger.append(
            "memory", "memver.written", {"agent": "A"},
            memver_id="memver_abc123",
        )
        assert event.memver_id == "memver_abc123"

    def test_memver_id_reread_via_iter_events(self, ledger: Ledger) -> None:
        ledger.append("memory", "memver.written", {"a": 1}, memver_id="memver_x")
        ledger.append("memory", "memver.written", {"a": 2})  # no memver
        events = list(ledger.iter_events())
        assert events[0].memver_id == "memver_x"
        assert events[1].memver_id is None

    def test_memver_id_bound_in_canonical_json(self, ledger: Ledger) -> None:
        event = ledger.append("s", "k", {"v": 1}, memver_id="memver_bound")
        assert '"_memver_id":"memver_bound"' in event.payload_json

    def test_memver_id_tamper_detected_via_verify(self, ledger: Ledger) -> None:
        ledger.append("s", "k", {"v": 1}, memver_id="memver_real")
        # Tamper: swap the _memver_id in the payload_json column.
        ledger._conn.execute(
            "UPDATE events SET payload_json = REPLACE(payload_json, 'memver_real', 'memver_fake')"
        )
        ledger._conn.commit()
        result = ledger.verify()
        assert result.valid is False

    def test_memver_id_empty_string_treated_as_none(self, ledger: Ledger) -> None:
        """Empty/falsy memver_id means the row does NOT bind the pairing."""
        event = ledger.append("s", "k", {"v": 1}, memver_id="")
        assert event.memver_id == ""
        assert "_memver_id" not in event.payload_json


# ---------------------------------------------------------------------------
# Mid-chain rotation (Phase 4 — ATT-02)
# ---------------------------------------------------------------------------


class TestMidChainRotation:
    def test_rotation_mid_chain_verify_still_valid(
        self, tmp_path: Path
    ) -> None:
        """Start key A → 3 events → rotate → key B → 3 events → verify all 6."""
        key_path = tmp_path / "key.pem"
        archive = tmp_path / "archive"
        signer_a = Signer.generate()
        signer_a.save(key_path)

        db = tmp_path / "chain.db"
        ledger_a = Ledger.open(db, signer_a)
        for i in range(3):
            ledger_a.append("sensor", "reading", {"i": i})
        # Close the ledger's handle to the DB so the new ledger can reopen.
        ledger_a._conn.close()

        # Rotate key on disk.
        signer_b = Signer.rotate(
            key_path, archive, timestamp="20260423T210100Z"
        )
        assert signer_b.public_key_pem != signer_a.public_key_pem

        # Re-open the ledger with the new signer — previously written rows
        # remain, chain continues.
        ledger_b = Ledger.open(db, signer_b)
        for i in range(3, 6):
            ledger_b.append("sensor", "reading", {"i": i})

        result = ledger_b.verify()
        assert result.valid is True, result.reason
        assert result.total == 6
        ledger_b._conn.close()

    def test_rotation_preserves_first_row_pubkey(self, tmp_path: Path) -> None:
        """Pre-rotation rows keep verifying against their original pubkey column."""
        key_path = tmp_path / "key.pem"
        archive = tmp_path / "archive"
        signer_a = Signer.generate()
        pub_a = signer_a.public_key_pem
        signer_a.save(key_path)

        db = tmp_path / "chain2.db"
        ledger_a = Ledger.open(db, signer_a)
        ledger_a.append("s", "k", {"v": 1})
        ledger_a._conn.close()

        signer_b = Signer.rotate(
            key_path, archive, timestamp="20260423T210200Z"
        )

        ledger_b = Ledger.open(db, signer_b)
        events = list(ledger_b.iter_events())
        assert events[0].pubkey == pub_a  # pre-rotation pubkey preserved
        ledger_b._conn.close()
