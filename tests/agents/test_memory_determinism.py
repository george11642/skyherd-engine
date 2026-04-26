"""Determinism guards for memory layer (Plan 01-07, MEM-09).

These tests assert:
  1. No HTTP call is made to Anthropic when SKYHERD_AGENTS != "managed".
  2. LocalMemoryStore IDs are deterministic (content-derived, no time/uuid).
  3. decide_write_path is time-invariant.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from skyherd.agents.memory import LocalMemoryStore, get_memory_store_manager
from skyherd.agents.memory_hook import post_cycle_write
from skyherd.agents.memory_paths import decide_write_path


class _Boom:
    """Sentinel constructor that raises on instantiation — proves no HTTP setup."""

    def __init__(self, *a, **kw):
        raise AssertionError("HTTP client constructed under SEED=42 — determinism broken!")


# ---------------------------------------------------------------------------
# No HTTP under local runtime
# ---------------------------------------------------------------------------


class TestNoHTTPUnderLocalRuntime:
    def test_factory_returns_local_without_managed_env(self, monkeypatch):
        monkeypatch.delenv("SKYHERD_AGENTS", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mgr = get_memory_store_manager("auto")
        assert isinstance(mgr, LocalMemoryStore)

    @pytest.mark.asyncio
    async def test_local_write_does_not_touch_anthropic(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("SKYHERD_AGENTS", raising=False)
        with patch("anthropic.AsyncAnthropic", _Boom):
            mgr = get_memory_store_manager("auto")
            sid = await mgr.ensure_store("test")
            await mgr.write_memory(sid, "/patterns/x.md", "hello")
            # If we got here, no AsyncAnthropic was constructed — PASS.

    @pytest.mark.asyncio
    async def test_post_cycle_write_no_http_under_local(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("SKYHERD_AGENTS", raising=False)
        session = SimpleNamespace(agent_name="PredatorPatternLearner")
        wake_event = {
            "classification": "coyote",
            "type": "predator.detected",
            "ranch_id": "ranch_a",
        }
        with patch("anthropic.AsyncAnthropic", _Boom):
            result = await post_cycle_write(
                session=session,
                wake_event=wake_event,
                tool_calls=[],
                ledger=None,
                broadcaster=None,
                store_id_map={"PredatorPatternLearner": "memstore_local_X"},
            )
            assert result is not None
            assert result["memory_version_id"].startswith("memver_")


# ---------------------------------------------------------------------------
# LocalMemoryStore ID determinism
# ---------------------------------------------------------------------------


class TestLocalStoreDeterminism:
    @pytest.mark.asyncio
    async def test_same_content_same_memver(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr1 = LocalMemoryStore()
        mgr2 = LocalMemoryStore()
        a = await mgr1.create_store("A")
        b = await mgr2.create_store("A")
        assert a.id == b.id
        ma = await mgr1.write_memory(a.id, "/p.md", "content")
        mb = await mgr2.write_memory(b.id, "/p.md", "content")
        assert ma.memory_version_id == mb.memory_version_id

    @pytest.mark.asyncio
    async def test_different_content_different_memver(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        s = await mgr.create_store("A")
        m1 = await mgr.write_memory(s.id, "/p.md", "content1")
        m2 = await mgr.write_memory(s.id, "/p.md", "content2")
        assert m1.memory_version_id != m2.memory_version_id


# ---------------------------------------------------------------------------
# decide_write_path is time-invariant + guard for forbidden imports
# ---------------------------------------------------------------------------


class TestDecideWritePathIsTimeInvariant:
    def test_same_inputs_same_output(self):
        evt = {
            "classification": "coyote.confirmed",
            "type": "predator.detected",
            "ranch_id": "ranch_a",
        }
        a = decide_write_path("PredatorPatternLearner", evt, [])
        b = decide_write_path("PredatorPatternLearner", evt, [])
        assert a == b

    def test_no_wall_clock_import_in_memory_paths(self):
        """Guard regression: memory_paths.py must never IMPORT non-deterministic stdlib.

        The module MAY mention these tokens in comments/docstrings (enforcing
        'we don't use X'); this test checks actual imports via the AST.
        """
        import ast
        import inspect

        from skyherd.agents import memory_paths

        src = inspect.getsource(memory_paths)
        tree = ast.parse(src)
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.add(node.module)
        forbidden_modules = {"datetime", "uuid", "time", "random"}
        hits = imported_names & forbidden_modules
        assert not hits, f"memory_paths.py imports forbidden non-deterministic modules: {hits}"

    def test_no_wall_clock_import_in_memory_module(self):
        """Guard: memory.py must also avoid non-deterministic stdlib imports."""
        import ast
        import inspect

        from skyherd.agents import memory

        src = inspect.getsource(memory)
        tree = ast.parse(src)
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.add(node.module)
        forbidden_modules = {"datetime", "uuid", "time", "random"}
        hits = imported_names & forbidden_modules
        assert not hits, f"memory.py imports forbidden non-deterministic modules: {hits}"
