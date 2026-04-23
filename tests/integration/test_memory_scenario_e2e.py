"""End-to-end integration: memory write + cross-agent read + dual receipts.

Demo-critical flow (MEM-05 + MEM-10):
  1. PredatorPatternLearner wakes on a coyote event; post_cycle_write writes
     ``patterns/coyote-crossings.md`` to its per-agent memory store.
  2. FenceLineDispatcher wakes on a subsequent fence breach; the hook writes
     a dispatch note.
  3. Ledger contains TWO entries with source='memory', kind='memver.written'.
  4. EventBroadcaster fanned out two 'memory.written' events.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from skyherd.agents.memory import LocalMemoryStore
from skyherd.agents.memory_hook import post_cycle_write


@pytest.mark.asyncio
async def test_full_chain_ppl_write_fld_read_dual_receipts(tmp_path, monkeypatch):
    """Demo narrative in one test:

    - PPL writes a coyote pattern.
    - FLD writes a dispatch note.
    - Ledger has 2 memver.written entries.
    - Broadcaster emitted 2 memory.written events.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SKYHERD_AGENTS", raising=False)  # Force LocalMemoryStore

    # Fakes for ledger + broadcaster — capture calls
    ledger = MagicMock()
    ledger.append = MagicMock()
    broadcaster = MagicMock()
    broadcaster._broadcast = MagicMock()

    # Set up fake stores (what AgentMesh._ensure_memory_stores would produce)
    mgr = LocalMemoryStore()
    ppl_store = await mgr.ensure_store("skyherd_predatorpatternlearner_ranch_a")
    fld_store = await mgr.ensure_store("skyherd_fencelinedispatcher_ranch_a")
    store_id_map = {
        "PredatorPatternLearner": ppl_store,
        "FenceLineDispatcher": fld_store,
    }

    # Act 1: PPL wake cycle (coyote detection)
    ppl_session = SimpleNamespace(agent_name="PredatorPatternLearner")
    ppl_event = {
        "classification": "coyote",
        "type": "predator.detected",
        "ranch_id": "ranch_a",
    }
    ppl_result = await post_cycle_write(
        ppl_session, ppl_event, [{"tool": "classify"}],
        ledger=ledger, broadcaster=broadcaster, store_id_map=store_id_map,
    )
    assert ppl_result is not None
    assert ppl_result["path"] == "/patterns/coyote-crossings.md"
    assert ppl_result["memory_version_id"].startswith("memver_")

    # Act 2: FLD wake cycle (fence breach)
    fld_session = SimpleNamespace(agent_name="FenceLineDispatcher")
    fld_event = {"segment": "seg_1", "type": "fence.breach"}
    fld_result = await post_cycle_write(
        fld_session, fld_event, [{"tool": "launch_drone"}],
        ledger=ledger, broadcaster=broadcaster, store_id_map=store_id_map,
    )
    assert fld_result is not None
    assert fld_result["path"].startswith("/notes/dispatch-")

    # Assert dual receipts (memver + ledger)
    assert ledger.append.call_count == 2
    calls = [c.kwargs for c in ledger.append.call_args_list]
    assert all(c["source"] == "memory" for c in calls)
    assert all(c["kind"] == "memver.written" for c in calls)
    # Distinct memvers
    memvers = {c["payload"]["memory_version_id"] for c in calls}
    assert len(memvers) == 2

    # Assert SSE fan-out
    assert broadcaster._broadcast.call_count == 2
    events = [c.args[0] for c in broadcaster._broadcast.call_args_list]
    assert events == ["memory.written", "memory.written"]


@pytest.mark.asyncio
async def test_cross_session_read_sees_ppl_pattern(tmp_path, monkeypatch):
    """PPL writes, FLD reads patterns/ prefix — same shared store would hold this.

    Simplified shared-store flow: assert list_memories(prefix='patterns/')
    returns the PPL entry after a PPL write, proving the read path works for
    downstream cross-agent coordination.
    """
    monkeypatch.chdir(tmp_path)
    mgr = LocalMemoryStore()
    store = await mgr.ensure_store("shared_patterns")
    await mgr.write_memory(store, "/patterns/coyote-crossings.md", "crossing observed")
    envelope = await mgr.list_memories(store, path_prefix="/patterns/")
    assert len(envelope.data) == 1
    assert envelope.data[0]["path"] == "/patterns/coyote-crossings.md"
