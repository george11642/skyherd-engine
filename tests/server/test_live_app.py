"""Live-mode /api/snapshot returns real world data, not mock data (BLD-03)."""

from __future__ import annotations

import tempfile

from fastapi.testclient import TestClient

from skyherd.attest.ledger import Ledger
from skyherd.attest.signer import Signer
from skyherd.server.app import create_app
from skyherd.world.world import make_world


def _make_live_client() -> TestClient:
    """Construct a FastAPI TestClient bound to the live (non-mock) factory path."""
    world = make_world(seed=42)  # Plan 01: no config_path needed
    signer = Signer.generate()
    tmp = tempfile.NamedTemporaryFile(suffix="_skyherd_ledger.db", delete=False)
    tmp.close()
    ledger = Ledger.open(tmp.name, signer)
    app = create_app(mock=False, mesh=None, world=world, ledger=ledger)
    return TestClient(app)


def test_live_snapshot_returns_real_world_data() -> None:
    """Live /api/snapshot returns ranch_a.yaml's 50 cows (mock has 12)."""
    client = _make_live_client()
    r = client.get("/api/snapshot")
    assert r.status_code == 200
    snap = r.json()
    assert len(snap["cows"]) == 50, (
        f"expected 50 cows from ranch_a.yaml live world, got {len(snap['cows'])} "
        "(mock path returns 12 — this indicates mock=False was not honored)"
    )
    assert snap["sim_time_s"] == 0.0, (
        "live world boots at sim_time_s=0.0; mock uses time.time() % 86400"
    )


def test_live_health_ok() -> None:
    """Health endpoint is stack-independent — must work in live mode too."""
    client = _make_live_client()
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
