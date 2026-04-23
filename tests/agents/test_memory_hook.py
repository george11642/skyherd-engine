"""Tests for post_cycle_write hook + AgentMesh._ensure_memory_stores (Plan 01-04)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from skyherd.agents.memory import Memory
from skyherd.agents.memory_hook import post_cycle_write


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _memory(path: str = "patterns/coyote-crossings.md", content_sha: str = "abc") -> Memory:
    return Memory(
        id="mem_A",
        memory_version_id="memver_B",
        content_sha256=content_sha,
        content_size_bytes=10,
        path="/" + path if not path.startswith("/") else path,
        created_at="1970-01-01T00:00:00Z",
        updated_at="1970-01-01T00:00:00Z",
    )


def _fake_mgr(memory: Memory, raises: Exception | None = None) -> MagicMock:
    mgr = MagicMock()
    if raises:
        mgr.write_memory = AsyncMock(side_effect=raises)
    else:
        mgr.write_memory = AsyncMock(return_value=memory)
    return mgr


# ---------------------------------------------------------------------------
# Hook no-op paths
# ---------------------------------------------------------------------------


class TestHookNoOps:
    @pytest.mark.asyncio
    async def test_noop_when_no_store_id_map(self):
        result = await post_cycle_write(
            session=SimpleNamespace(agent_name="X"),
            wake_event={},
            tool_calls=[],
            store_id_map=None,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_noop_when_agent_name_missing(self):
        result = await post_cycle_write(
            session=SimpleNamespace(),
            wake_event={},
            tool_calls=[],
            store_id_map={"X": "memstore_X"},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_noop_when_agent_not_in_map(self):
        result = await post_cycle_write(
            session=SimpleNamespace(agent_name="GrazingOptimizer"),
            wake_event={},
            tool_calls=[],
            store_id_map={"PredatorPatternLearner": "memstore_X"},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_noop_on_unknown_agent_in_decide_write_path(self, monkeypatch):
        """decide_write_path raises ValueError — hook logs warning and returns None."""
        result = await post_cycle_write(
            session=SimpleNamespace(agent_name="NotRealAgent"),
            wake_event={},
            tool_calls=[],
            store_id_map={"NotRealAgent": "memstore_X"},
        )
        assert result is None


# ---------------------------------------------------------------------------
# Hook happy path
# ---------------------------------------------------------------------------


class TestHookWrites:
    @pytest.mark.asyncio
    async def test_writes_memory_for_mapped_agent(self, monkeypatch):
        mgr = _fake_mgr(_memory())
        monkeypatch.setattr(
            "skyherd.agents.memory.get_memory_store_manager", lambda runtime="auto": mgr
        )
        session = SimpleNamespace(agent_name="PredatorPatternLearner")
        wake_event = {
            "classification": "coyote.confirmed",
            "type": "predator.detected",
            "ranch_id": "ranch_a",
        }
        result = await post_cycle_write(
            session=session,
            wake_event=wake_event,
            tool_calls=[],
            store_id_map={"PredatorPatternLearner": "memstore_X"},
        )
        assert result is not None
        assert result["memory_version_id"] == "memver_B"
        # write_memory was awaited with (store_id, path, content)
        args = mgr.write_memory.await_args.args
        assert args[0] == "memstore_X"
        assert args[1] == "patterns/coyote-crossings.md"
        assert "coyote" in args[2]

    @pytest.mark.asyncio
    async def test_pairs_with_ledger_append(self, monkeypatch):
        mgr = _fake_mgr(_memory())
        monkeypatch.setattr(
            "skyherd.agents.memory.get_memory_store_manager", lambda runtime="auto": mgr
        )
        ledger = MagicMock()
        await post_cycle_write(
            session=SimpleNamespace(agent_name="PredatorPatternLearner"),
            wake_event={"classification": "coyote.confirmed", "ranch_id": "ranch_a", "type": "predator.detected"},
            tool_calls=[],
            ledger=ledger,
            store_id_map={"PredatorPatternLearner": "memstore_X"},
        )
        ledger.append.assert_called_once()
        kwargs = ledger.append.call_args.kwargs
        assert kwargs["source"] == "memory"
        assert kwargs["kind"] == "memver.written"
        assert kwargs["payload"]["memory_version_id"] == "memver_B"

    @pytest.mark.asyncio
    async def test_emits_memory_written_sse(self, monkeypatch):
        mgr = _fake_mgr(_memory())
        monkeypatch.setattr(
            "skyherd.agents.memory.get_memory_store_manager", lambda runtime="auto": mgr
        )
        broadcaster = MagicMock()
        await post_cycle_write(
            session=SimpleNamespace(agent_name="PredatorPatternLearner"),
            wake_event={"classification": "coyote.confirmed", "ranch_id": "ranch_a", "type": "predator.detected"},
            tool_calls=[],
            broadcaster=broadcaster,
            store_id_map={"PredatorPatternLearner": "memstore_X"},
        )
        broadcaster._broadcast.assert_called_once()
        args = broadcaster._broadcast.call_args.args
        assert args[0] == "memory.written"
        assert args[1]["memory_version_id"] == "memver_B"

    @pytest.mark.asyncio
    async def test_ledger_payload_has_exact_keys(self, monkeypatch):
        mgr = _fake_mgr(_memory())
        monkeypatch.setattr(
            "skyherd.agents.memory.get_memory_store_manager", lambda runtime="auto": mgr
        )
        ledger = MagicMock()
        await post_cycle_write(
            session=SimpleNamespace(agent_name="PredatorPatternLearner"),
            wake_event={"classification": "coyote.confirmed", "ranch_id": "ranch_a", "type": "predator.detected"},
            tool_calls=[],
            ledger=ledger,
            store_id_map={"PredatorPatternLearner": "memstore_X"},
        )
        payload = ledger.append.call_args.kwargs["payload"]
        assert set(payload.keys()) == {
            "agent", "memory_store_id", "memory_id",
            "memory_version_id", "content_sha256", "path",
        }


# ---------------------------------------------------------------------------
# Failure isolation
# ---------------------------------------------------------------------------


class TestHookFailureIsolation:
    @pytest.mark.asyncio
    async def test_hook_propagates_write_failure(self, monkeypatch):
        """write_memory failure: hook RAISES out; caller's try/except is the safety net."""
        mgr = _fake_mgr(_memory(), raises=RuntimeError("boom"))
        monkeypatch.setattr(
            "skyherd.agents.memory.get_memory_store_manager", lambda runtime="auto": mgr
        )
        with pytest.raises(RuntimeError, match="boom"):
            await post_cycle_write(
                session=SimpleNamespace(agent_name="PredatorPatternLearner"),
                wake_event={"classification": "coyote", "ranch_id": "ranch_a", "type": "predator.detected"},
                tool_calls=[],
                store_id_map={"PredatorPatternLearner": "memstore_X"},
            )

    @pytest.mark.asyncio
    async def test_ledger_failure_does_not_block_sse_emit(self, monkeypatch):
        mgr = _fake_mgr(_memory())
        monkeypatch.setattr(
            "skyherd.agents.memory.get_memory_store_manager", lambda runtime="auto": mgr
        )
        ledger = MagicMock()
        ledger.append.side_effect = Exception("ledger down")
        broadcaster = MagicMock()
        await post_cycle_write(
            session=SimpleNamespace(agent_name="PredatorPatternLearner"),
            wake_event={"classification": "coyote", "ranch_id": "ranch_a", "type": "predator.detected"},
            tool_calls=[],
            ledger=ledger,
            broadcaster=broadcaster,
            store_id_map={"PredatorPatternLearner": "memstore_X"},
        )
        broadcaster._broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcaster_failure_does_not_block_return(self, monkeypatch):
        mgr = _fake_mgr(_memory())
        monkeypatch.setattr(
            "skyherd.agents.memory.get_memory_store_manager", lambda runtime="auto": mgr
        )
        broadcaster = MagicMock()
        broadcaster._broadcast.side_effect = Exception("sse down")
        result = await post_cycle_write(
            session=SimpleNamespace(agent_name="PredatorPatternLearner"),
            wake_event={"classification": "coyote", "ranch_id": "ranch_a", "type": "predator.detected"},
            tool_calls=[],
            broadcaster=broadcaster,
            store_id_map={"PredatorPatternLearner": "memstore_X"},
        )
        assert result is not None


# ---------------------------------------------------------------------------
# AgentMesh._ensure_memory_stores
# ---------------------------------------------------------------------------


class TestMeshEnsureMemoryStores:
    @pytest.mark.asyncio
    async def test_creates_seven_stores(self, tmp_path, monkeypatch):
        """Phase 02 adds CrossRanchCoordinator as the 6th agent → 7 stores total
        (1 shared + 6 per-agent)."""
        monkeypatch.chdir(tmp_path)
        from skyherd.agents.mesh import AgentMesh

        mesh = AgentMesh()
        ids = await mesh._ensure_memory_stores()
        assert len(ids) == 7
        assert "_shared" in ids
        for name in ["FenceLineDispatcher", "HerdHealthWatcher",
                     "PredatorPatternLearner", "GrazingOptimizer", "CalvingWatch",
                     "CrossRanchCoordinator"]:
            assert name in ids
            assert ids[name].startswith("memstore_")

    @pytest.mark.asyncio
    async def test_is_idempotent_via_cache(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from skyherd.agents.mesh import AgentMesh

        mesh = AgentMesh()
        ids_first = await mesh._ensure_memory_stores()
        # Second call should read from cache file — no new stores created.
        ids_second = await mesh._ensure_memory_stores()
        assert ids_first == ids_second


# ---------------------------------------------------------------------------
# Integration: run_handler_cycle invokes the hook
# ---------------------------------------------------------------------------


class TestHandlerBaseIntegration:
    @pytest.mark.asyncio
    async def test_hook_invoked_and_tool_calls_preserved(self, monkeypatch):
        """run_handler_cycle → _run_local_with_cache returns sentinel, hook runs, sentinel preserved."""
        import skyherd.agents._handler_base as hb

        sentinel = [{"tool": "noop", "input": {}}]

        async def _fake_local(**kwargs):
            return sentinel

        monkeypatch.setattr(hb, "_run_local_with_cache", _fake_local)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        monkeypatch.delenv("SKYHERD_AGENTS", raising=False)

        mgr = _fake_mgr(_memory())
        monkeypatch.setattr(
            "skyherd.agents.memory.get_memory_store_manager", lambda runtime="auto": mgr
        )

        session = SimpleNamespace(
            agent_name="FenceLineDispatcher",
            wake_events_consumed=[{"segment": "seg_1", "type": "fence.breach"}],
            _memory_store_id_map={"FenceLineDispatcher": "memstore_X"},
            _ledger_ref=MagicMock(),
            _broadcaster_ref=MagicMock(),
        )
        wake_event = {"segment": "seg_1", "type": "fence.breach"}
        result = await hb.run_handler_cycle(
            session=session,
            wake_event=wake_event,
            sdk_client=MagicMock(),  # non-None triggers path
            cached_payload={"system": [], "messages": []},
        )
        assert result == sentinel
        session._broadcaster_ref._broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_hook_failure_swallowed_by_handler_base(self, monkeypatch, caplog):
        """If post_cycle_write raises, run_handler_cycle logs a warning and returns tool_calls."""
        import skyherd.agents._handler_base as hb

        sentinel = [{"tool": "noop"}]

        async def _fake_local(**kwargs):
            return sentinel

        monkeypatch.setattr(hb, "_run_local_with_cache", _fake_local)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        monkeypatch.delenv("SKYHERD_AGENTS", raising=False)

        async def _raise(*args, **kwargs):
            raise RuntimeError("hook boom")

        # Patch post_cycle_write at the _handler_base import site.
        import skyherd.agents.memory_hook as mh
        monkeypatch.setattr(mh, "post_cycle_write", _raise)

        session = SimpleNamespace(
            agent_name="FenceLineDispatcher",
            wake_events_consumed=[{"segment": "seg_1", "type": "fence.breach"}],
            _memory_store_id_map={"FenceLineDispatcher": "memstore_X"},
            _ledger_ref=None,
            _broadcaster_ref=None,
        )
        import logging
        caplog.set_level(logging.WARNING)
        result = await hb.run_handler_cycle(
            session=session,
            wake_event={"segment": "seg_1", "type": "fence.breach"},
            sdk_client=MagicMock(),
            cached_payload={"system": [], "messages": []},
        )
        assert result == sentinel
        assert any("memory post-cycle write failed" in rec.message for rec in caplog.records)
