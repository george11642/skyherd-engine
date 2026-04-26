"""Tests for Phase-4 attestation API endpoints.

Endpoints under test:
- GET /api/attest/by-hash/{hash}  (ATT-01)
- GET /api/attest/pair/{memver_id}  (ATT-04)

Exercises both mock and live paths. Live path uses a real on-disk Ledger
wired via create_app(ledger=...).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.server.app import create_app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_app():
    return create_app(mock=True)


@pytest_asyncio.fixture
async def mock_client(mock_app):
    async with AsyncClient(
        transport=ASGITransport(app=mock_app, raise_app_exceptions=True),
        base_url="http://test",
    ) as c:
        yield c


@pytest.fixture
def live_ledger(tmp_path: Path) -> tuple[Ledger, str, str]:
    """3-event ledger with one memver-paired row. Returns (ledger, head_hash, memver_id)."""
    signer = Signer.generate()
    db = tmp_path / "live_attest.db"
    ledger = Ledger.open(db, signer)
    ledger.append("sensor.water", "water.low", {"tank": 1})
    ledger.append(
        "memory", "memver.written", {"agent": "A", "memory_version_id": "memver_live42"},
        memver_id="memver_live42",
    )
    head = ledger.append("sensor.fence", "fence.breach", {"fence": "north"})
    return ledger, head.event_hash, "memver_live42"


@pytest_asyncio.fixture
async def live_client(live_ledger):
    ledger, _, _ = live_ledger
    app = create_app(mock=False, ledger=ledger)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=True),
        base_url="http://test",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# /api/attest/by-hash/{hash}
# ---------------------------------------------------------------------------


class TestAttestByHashMock:
    @pytest.mark.asyncio
    async def test_mock_returns_chain(self, mock_client: AsyncClient):
        resp = await mock_client.get("/api/attest/by-hash/" + "ab" * 16)
        assert resp.status_code == 200
        body = resp.json()
        assert body["target"] == "ab" * 16
        assert len(body["chain"]) == 3
        assert body["chain"][0]["prev_hash"] == "GENESIS"

    @pytest.mark.asyncio
    async def test_rejects_non_hex_suffix(self, mock_client: AsyncClient):
        # Alphanumeric mix with non-hex char → 400
        resp = await mock_client.get("/api/attest/by-hash/zz" + "a" * 14)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_non_hex_hash(self, mock_client: AsyncClient):
        resp = await mock_client.get("/api/attest/by-hash/not-hex-$$$")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_oversized_hash(self, mock_client: AsyncClient):
        resp = await mock_client.get("/api/attest/by-hash/" + "a" * 200)
        assert resp.status_code == 400


class TestAttestByHashLive:
    @pytest.mark.asyncio
    async def test_live_chain_back_to_genesis(
        self, live_client: AsyncClient, live_ledger
    ):
        _, head_hash, _ = live_ledger
        resp = await live_client.get(f"/api/attest/by-hash/{head_hash}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["target"] == head_hash
        assert len(body["chain"]) == 3
        assert body["chain"][0]["prev_hash"] == "GENESIS"
        assert body["chain"][-1]["event_hash"] == head_hash

    @pytest.mark.asyncio
    async def test_live_404_unknown_hash(self, live_client: AsyncClient):
        resp = await live_client.get("/api/attest/by-hash/" + "de" * 16)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /api/attest/pair/{memver_id}
# ---------------------------------------------------------------------------


class TestAttestPairMock:
    @pytest.mark.asyncio
    async def test_mock_returns_pair(self, mock_client: AsyncClient):
        resp = await mock_client.get("/api/attest/pair/memver_abc123")
        assert resp.status_code == 200
        body = resp.json()
        assert body["memver_id"] == "memver_abc123"
        assert "ledger_entry" in body
        assert "memver" in body
        assert body["memver"]["id"] == "memver_abc123"

    @pytest.mark.asyncio
    async def test_rejects_invalid_memver(self, mock_client: AsyncClient):
        resp = await mock_client.get("/api/attest/pair/has spaces!")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_oversized_memver(self, mock_client: AsyncClient):
        resp = await mock_client.get("/api/attest/pair/" + "a" * 200)
        assert resp.status_code == 400


class TestAttestPairLive:
    @pytest.mark.asyncio
    async def test_live_matches_memver_id_field(
        self, live_client: AsyncClient, live_ledger
    ):
        _, _, memver_id = live_ledger
        resp = await live_client.get(f"/api/attest/pair/{memver_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["memver_id"] == memver_id
        assert body["ledger_entry"]["memver_id"] == memver_id
        assert body["memver"]["agent"] == "A"

    @pytest.mark.asyncio
    async def test_live_404_unknown_memver(self, live_client: AsyncClient):
        resp = await live_client.get("/api/attest/pair/memver_doesnotexist")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_live_matches_legacy_payload_field(self, tmp_path: Path):
        """Pre-Phase-4 rows only had memory_version_id in the payload, no
        memver_id field. The endpoint must still pair them."""
        signer = Signer.generate()
        db = tmp_path / "legacy.db"
        ledger = Ledger.open(db, signer)
        # Legacy path — no memver_id kwarg, just payload.
        ledger.append(
            "memory",
            "memver.written",
            {"agent": "LegacyAgent", "memory_version_id": "memver_legacy"},
        )
        app = create_app(mock=False, ledger=ledger)
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=True),
            base_url="http://test",
        ) as c:
            resp = await c.get("/api/attest/pair/memver_legacy")
            assert resp.status_code == 200
            assert resp.json()["memver_id"] == "memver_legacy"
