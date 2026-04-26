"""Tests for MemoryStoreManager + LocalMemoryStore (Plan 01-02).

All external Anthropic REST calls are mocked via AsyncMock.
Target: ≥90% line coverage of src/skyherd/agents/memory.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from skyherd.agents.managed import ManagedAgentsUnavailable
from skyherd.agents.memory import (
    ListEnvelope,
    LocalMemoryStore,
    Memory,
    MemoryStore,
    MemoryStoreBase,
    MemoryStoreManager,
    MemoryVersion,
    get_memory_store_manager,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store_response(name: str = "foo", archived: bool = False) -> dict:
    return {
        "id": "memstore_018S1WJAA5mpXW9mTH3YXqzE",
        "name": name,
        "description": None,
        "type": "memory_store",
        "created_at": "2026-04-23T20:10:00Z",
        "updated_at": "2026-04-23T20:10:00Z",
        "archived_at": "2026-04-23T20:11:00Z" if archived else None,
    }


def _make_memory_response(path: str = "/patterns/x.md") -> dict:
    return {
        "id": "mem_0126mdrYVnARX4Q9iteMiNaB",
        "memory_version_id": "memver_01XRSVdKC1McTbhVbVF5T47E",
        "content_sha256": "a" * 64,
        "content_size_bytes": 128,
        "path": path,
        "created_at": "2026-04-23T20:10:00Z",
        "updated_at": "2026-04-23T20:10:00Z",
    }


def _mock_manager(monkeypatch, tmp_path: Path) -> tuple[MemoryStoreManager, AsyncMock]:
    """Build a MemoryStoreManager with an AsyncMock anthropic client."""
    client = AsyncMock()
    # client.post / client.get are AsyncMock by default on AsyncMock instance
    mgr = MemoryStoreManager(
        api_key="sk-test-fake",
        client=client,
        store_ids_path=str(tmp_path / "store_ids.json"),
    )
    return mgr, client


# ---------------------------------------------------------------------------
# TestManagedGuard
# ---------------------------------------------------------------------------


class TestManagedGuard:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ManagedAgentsUnavailable):
            MemoryStoreManager()


# ---------------------------------------------------------------------------
# TestFactory
# ---------------------------------------------------------------------------


class TestFactory:
    def test_local_runtime_returns_local(self):
        assert isinstance(get_memory_store_manager("local"), LocalMemoryStore)

    def test_auto_without_env_returns_local(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("SKYHERD_AGENTS", raising=False)
        assert isinstance(get_memory_store_manager("auto"), LocalMemoryStore)

    def test_auto_with_managed_env_and_key_returns_manager(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        monkeypatch.setenv("SKYHERD_AGENTS", "managed")
        monkeypatch.chdir(tmp_path)
        # Patch AsyncAnthropic so construction is cheap + doesn't hit network.
        with patch("anthropic.AsyncAnthropic", AsyncMock()):
            mgr = get_memory_store_manager("auto")
        assert isinstance(mgr, MemoryStoreManager)

    def test_auto_managed_env_but_no_key_returns_local(self, monkeypatch):
        monkeypatch.setenv("SKYHERD_AGENTS", "managed")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert isinstance(get_memory_store_manager("auto"), LocalMemoryStore)


# ---------------------------------------------------------------------------
# TestRestParsing
# ---------------------------------------------------------------------------


class TestRestParsing:
    @pytest.mark.asyncio
    async def test_create_store_parses_response(self, monkeypatch, tmp_path):
        mgr, client = _mock_manager(monkeypatch, tmp_path)
        client.post.return_value = _make_store_response()
        result = await mgr.create_store(name="foo")
        assert isinstance(result, MemoryStore)
        assert result.id.startswith("memstore_")
        # Beta header present on this call.
        opts = client.post.await_args.kwargs["options"]
        assert opts["headers"]["anthropic-beta"] == "managed-agents-2026-04-01"

    @pytest.mark.asyncio
    async def test_write_memory_parses_response(self, monkeypatch, tmp_path):
        mgr, client = _mock_manager(monkeypatch, tmp_path)
        client.post.return_value = _make_memory_response()
        result = await mgr.write_memory("memstore_X", "/patterns/coyote.md", "body")
        assert isinstance(result, Memory)
        assert result.memory_version_id.startswith("memver_")
        assert result.id.startswith("mem_")

    @pytest.mark.asyncio
    async def test_write_memory_prepends_slash(self, monkeypatch, tmp_path):
        """Path normalization — live API requires leading '/'."""
        mgr, client = _mock_manager(monkeypatch, tmp_path)
        client.post.return_value = _make_memory_response()
        await mgr.write_memory("memstore_X", "patterns/coyote.md", "body")
        body = client.post.await_args.kwargs["body"]
        assert body["path"] == "/patterns/coyote.md"

    @pytest.mark.asyncio
    async def test_list_memories_parses_envelope(self, monkeypatch, tmp_path):
        mgr, client = _mock_manager(monkeypatch, tmp_path)
        client.get.return_value = {
            "data": [_make_memory_response(), _make_memory_response("/patterns/y.md")],
            "prefixes": ["patterns/"],
        }
        envelope = await mgr.list_memories("memstore_X", path_prefix="/patterns/")
        assert isinstance(envelope, ListEnvelope)
        assert len(envelope.data) == 2

    @pytest.mark.asyncio
    async def test_list_versions_parses_list(self, monkeypatch, tmp_path):
        mgr, client = _mock_manager(monkeypatch, tmp_path)
        client.get.return_value = {
            "data": [
                {
                    "id": "memver_01XRSVdKC1McTbhVbVF5T47E",
                    "operation": "created",
                    "created_by": {"type": "api_actor", "api_key_id": "apikey_X"},
                    "path": "/patterns/x.md",
                }
            ]
        }
        versions = await mgr.list_versions("memstore_X")
        assert isinstance(versions, list)
        assert len(versions) == 1
        assert isinstance(versions[0], MemoryVersion)

    @pytest.mark.asyncio
    async def test_archive_store_parses_response(self, monkeypatch, tmp_path):
        mgr, client = _mock_manager(monkeypatch, tmp_path)
        client.post.return_value = _make_store_response(archived=True)
        result = await mgr.archive_store("memstore_X")
        assert result.archived_at is not None

    @pytest.mark.asyncio
    async def test_list_stores_parses_list(self, monkeypatch, tmp_path):
        mgr, client = _mock_manager(monkeypatch, tmp_path)
        client.get.return_value = {"data": [_make_store_response(), _make_store_response("bar")]}
        stores = await mgr.list_stores()
        assert len(stores) == 2


# ---------------------------------------------------------------------------
# TestBetaHeader (CRITICAL)
# ---------------------------------------------------------------------------


class TestBetaHeader:
    @pytest.mark.asyncio
    async def test_every_rest_call_includes_beta_header(self, monkeypatch, tmp_path):
        mgr, client = _mock_manager(monkeypatch, tmp_path)
        client.post.return_value = _make_store_response()
        client.get.return_value = {"data": []}

        # 5+ ops — assert header present on each.
        await mgr.create_store(name="x")
        await mgr.list_stores()
        await mgr.list_memories("memstore_X")
        await mgr.list_versions("memstore_X")
        await mgr.archive_store("memstore_X")
        client.post.return_value = _make_memory_response()
        await mgr.write_memory("memstore_X", "/p.md", "c")

        # Each awaited call must have had the beta header.
        post_calls = client.post.await_args_list
        get_calls = client.get.await_args_list
        for call in post_calls + get_calls:
            opts = call.kwargs["options"]
            assert opts["headers"]["anthropic-beta"] == "managed-agents-2026-04-01", (
                f"Call missing beta header: {call!r}"
            )
        # Headline: at least 5 operations (assertion anchors for must_haves grep)
        assert len(post_calls) + len(get_calls) >= 5  # anthropic-beta check


# ---------------------------------------------------------------------------
# TestLocalShimParity
# ---------------------------------------------------------------------------


class TestLocalShimParity:
    @pytest.mark.asyncio
    async def test_local_create_store_is_deterministic(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr1 = LocalMemoryStore()
        mgr2 = LocalMemoryStore()
        a = await mgr1.create_store("foo")
        b = await mgr2.create_store("foo")
        assert a.id == b.id

    @pytest.mark.asyncio
    async def test_local_write_memory_appends_jsonl(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        store = await mgr.create_store("foo")
        await mgr.write_memory(store.id, "/p.md", "hello")
        jsonl = Path("runtime/memory") / f"{store.id}.jsonl"
        lines = [ln for ln in jsonl.read_text().splitlines() if ln.strip()]
        assert len(lines) == 1
        assert "hello" in lines[0]

    @pytest.mark.asyncio
    async def test_local_list_memories_returns_envelope(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        store = await mgr.create_store("foo")
        await mgr.write_memory(store.id, "/p1.md", "c1")
        await mgr.write_memory(store.id, "/p2.md", "c2")
        env = await mgr.list_memories(store.id)
        assert isinstance(env, ListEnvelope)
        assert len(env.data) == 2

    @pytest.mark.asyncio
    async def test_local_memver_id_is_content_derived(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        store = await mgr.create_store("foo")
        m1 = await mgr.write_memory(store.id, "/p.md", "content")
        m2 = await mgr.write_memory(store.id, "/p.md", "content")
        assert m1.memory_version_id == m2.memory_version_id

    @pytest.mark.asyncio
    async def test_local_memver_id_changes_with_content(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        store = await mgr.create_store("foo")
        m1 = await mgr.write_memory(store.id, "/p.md", "content1")
        m2 = await mgr.write_memory(store.id, "/p.md", "content2")
        assert m1.memory_version_id != m2.memory_version_id

    @pytest.mark.asyncio
    async def test_local_response_shape_matches_managed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        store = await mgr.create_store("foo")
        await mgr.write_memory(store.id, "/p.md", "c")
        env = await mgr.list_memories(store.id)
        assert hasattr(env, "data")
        assert hasattr(env, "prefixes")

    @pytest.mark.asyncio
    async def test_local_list_versions_works(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        store = await mgr.create_store("foo")
        await mgr.write_memory(store.id, "/p.md", "c")
        versions = await mgr.list_versions(store.id)
        assert len(versions) == 1
        assert versions[0].id.startswith("memver_")

    @pytest.mark.asyncio
    async def test_local_archive_and_list(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        await mgr.create_store("foo")
        stores_before = await mgr.list_stores()
        assert len(stores_before) == 1
        archived = await mgr.archive_store(stores_before[0].id)
        assert archived.archived_at is not None
        stores_after = await mgr.list_stores()
        assert len(stores_after) == 0

    @pytest.mark.asyncio
    async def test_local_list_memories_filters_by_prefix(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        store = await mgr.create_store("foo")
        await mgr.write_memory(store.id, "/patterns/x.md", "c1")
        await mgr.write_memory(store.id, "/notes/y.md", "c2")
        env = await mgr.list_memories(store.id, path_prefix="/patterns/")
        assert len(env.data) == 1
        assert env.data[0]["path"] == "/patterns/x.md"


# ---------------------------------------------------------------------------
# TestEnsureStoreIdempotent
# ---------------------------------------------------------------------------


class TestEnsureStoreIdempotent:
    @pytest.mark.asyncio
    async def test_ensure_store_writes_cache_file(self, tmp_path, monkeypatch):
        mgr, client = _mock_manager(monkeypatch, tmp_path)
        client.post.return_value = _make_store_response("unique_name")
        sid = await mgr.ensure_store("unique_name")
        assert sid.startswith("memstore_")
        cache = tmp_path / "store_ids.json"
        assert cache.exists()
        cached = json.loads(cache.read_text())
        assert cached["unique_name"] == sid

    @pytest.mark.asyncio
    async def test_ensure_store_skips_create_when_cached(self, tmp_path, monkeypatch):
        mgr, client = _mock_manager(monkeypatch, tmp_path)
        client.post.return_value = _make_store_response("cachedname")
        await mgr.ensure_store("cachedname")
        assert client.post.await_count == 1
        # Second call: should NOT create again.
        await mgr.ensure_store("cachedname")
        assert client.post.await_count == 1

    @pytest.mark.asyncio
    async def test_local_ensure_store_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        a = await mgr.ensure_store("shared")
        b = await mgr.ensure_store("shared")
        assert a == b
        # Cache file present.
        cache = tmp_path / "runtime" / "memory_store_ids.json"
        assert cache.exists()


# ---------------------------------------------------------------------------
# Sanity — Base class interface is abstract
# ---------------------------------------------------------------------------


class TestBaseInterface:
    @pytest.mark.asyncio
    async def test_base_create_store_raises_not_implemented(self):
        base = MemoryStoreBase()
        with pytest.raises(NotImplementedError):
            await base.create_store("x")

    @pytest.mark.asyncio
    async def test_base_write_memory_raises_not_implemented(self):
        base = MemoryStoreBase()
        with pytest.raises(NotImplementedError):
            await base.write_memory("s", "/p", "c")

    @pytest.mark.asyncio
    async def test_base_ensure_store_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            await MemoryStoreBase().ensure_store("x")

    @pytest.mark.asyncio
    async def test_base_list_stores_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            await MemoryStoreBase().list_stores()

    @pytest.mark.asyncio
    async def test_base_archive_store_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            await MemoryStoreBase().archive_store("s")

    @pytest.mark.asyncio
    async def test_base_list_memories_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            await MemoryStoreBase().list_memories("s")

    @pytest.mark.asyncio
    async def test_base_list_versions_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            await MemoryStoreBase().list_versions("s")


# ---------------------------------------------------------------------------
# Edge cases (cache parse, prefix, archive unknown, filter by memory_id, etc.)
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_normalize_empty_path_returns_slash(self):
        from skyherd.agents.memory import _normalize_path

        assert _normalize_path("") == "/"
        assert _normalize_path(None) == "/"  # type: ignore[arg-type]

    def test_normalize_path_keeps_leading_slash(self):
        from skyherd.agents.memory import _normalize_path

        assert _normalize_path("/already/slash") == "/already/slash"

    def test_manager_loads_existing_cache_file(self, tmp_path, monkeypatch):
        cache = tmp_path / "store_ids.json"
        cache.write_text(json.dumps({"preexisting": "memstore_XYZ"}))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        client = AsyncMock()
        mgr = MemoryStoreManager(api_key="sk-test-fake", client=client, store_ids_path=str(cache))
        assert mgr._store_ids["preexisting"] == "memstore_XYZ"

    def test_manager_tolerates_corrupted_cache_file(self, tmp_path):
        cache = tmp_path / "store_ids.json"
        cache.write_text("not json {{{")
        client = AsyncMock()
        mgr = MemoryStoreManager(api_key="sk-test-fake", client=client, store_ids_path=str(cache))
        # Should not raise; should fall back to empty dict.
        assert mgr._store_ids == {}

    def test_local_loads_existing_cache_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cache = tmp_path / "runtime" / "memory_store_ids.json"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"shared": "memstore_deadbeef"}))
        mgr = LocalMemoryStore()
        assert mgr._store_ids["shared"] == "memstore_deadbeef"

    def test_local_tolerates_corrupted_cache_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cache = tmp_path / "runtime" / "memory_store_ids.json"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text("garbage {{{")
        mgr = LocalMemoryStore()
        assert mgr._store_ids == {}

    @pytest.mark.asyncio
    async def test_local_list_memories_empty_store(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        store = await mgr.create_store("empty")
        env = await mgr.list_memories(store.id)
        assert env.data == []

    @pytest.mark.asyncio
    async def test_local_list_memories_on_nonexistent_store(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        env = await mgr.list_memories("memstore_doesnotexist")
        assert env.data == []

    @pytest.mark.asyncio
    async def test_local_list_versions_on_nonexistent_store(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        assert await mgr.list_versions("memstore_doesnotexist") == []

    @pytest.mark.asyncio
    async def test_local_archive_unknown_store(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        archived = await mgr.archive_store("memstore_unknown")
        assert archived.archived_at is not None

    @pytest.mark.asyncio
    async def test_local_list_versions_filter_by_memory_id(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = LocalMemoryStore()
        store = await mgr.create_store("x")
        m1 = await mgr.write_memory(store.id, "/p1.md", "c1")
        await mgr.write_memory(store.id, "/p2.md", "c2")
        versions = await mgr.list_versions(store.id, memory_id=m1.id)
        assert len(versions) == 1

    @pytest.mark.asyncio
    async def test_local_ensure_store_reconstructs_from_cache(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Pre-seed cache but not self._stores: ensures reconstruction branch.
        cache = tmp_path / "runtime" / "memory_store_ids.json"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"name_x": "memstore_deadbeef0123456789abcdef"}))
        mgr = LocalMemoryStore()
        sid = await mgr.ensure_store("name_x")
        assert sid == "memstore_deadbeef0123456789abcdef"
        # Now write succeeds because we reconstructed the in-memory state.
        await mgr.write_memory(sid, "/p.md", "c")
        env = await mgr.list_memories(sid)
        assert len(env.data) == 1
