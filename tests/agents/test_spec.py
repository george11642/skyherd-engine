"""Tests for AgentSpec and prompt-caching block shape."""

from __future__ import annotations

from skyherd.agents.session import build_cached_messages
from skyherd.agents.spec import AgentSpec


def _make_spec(**kwargs) -> AgentSpec:
    defaults = dict(
        name="TestAgent",
        system_prompt_template_path="src/skyherd/agents/prompts/fenceline_dispatcher.md",
        wake_topics=["skyherd/+/fence/+"],
        mcp_servers=["sensor_mcp"],
        skills=[],
        checkpoint_interval_s=3600,
        max_idle_s_before_checkpoint=600,
        model="claude-opus-4-7",
    )
    defaults.update(kwargs)
    return AgentSpec(**defaults)


class TestAgentSpec:
    def test_name_stored(self):
        spec = _make_spec(name="FencelineDispatcher")
        assert spec.name == "FencelineDispatcher"

    def test_wake_topics_list(self):
        spec = _make_spec(wake_topics=["skyherd/+/fence/+", "skyherd/+/thermal/+"])
        assert len(spec.wake_topics) == 2
        assert "skyherd/+/fence/+" in spec.wake_topics

    def test_mcp_servers_stored(self):
        spec = _make_spec(mcp_servers=["sensor_mcp", "galileo_mcp"])
        assert "sensor_mcp" in spec.mcp_servers
        assert "galileo_mcp" in spec.mcp_servers

    def test_default_model(self):
        spec = _make_spec()
        assert spec.model == "claude-opus-4-7"

    def test_checkpoint_interval(self):
        spec = _make_spec(checkpoint_interval_s=86400)
        assert spec.checkpoint_interval_s == 86400


class TestBuildCachedMessages:
    """Verify prompt-caching block shape for the Anthropic prompt-cache API."""

    def test_returns_dict_with_system_and_messages(self):
        payload = build_cached_messages("sys", [], "user msg")
        assert "system" in payload
        assert "messages" in payload

    def test_system_is_list(self):
        payload = build_cached_messages("sys", [], "user msg")
        assert isinstance(payload["system"], list)

    def test_system_prompt_block_has_cache_control(self):
        payload = build_cached_messages("sys prompt", [], "user msg")
        sys_blocks = payload["system"]
        # At minimum the system prompt block should carry cache_control
        block = sys_blocks[0]
        assert block.get("type") == "text"
        assert block.get("cache_control") == {"type": "ephemeral"}
        assert "sys prompt" in block["text"]

    def test_skill_blocks_have_cache_control(self):
        skills = ["skill content alpha", "skill content beta"]
        payload = build_cached_messages("sys", skills, "user msg")
        # All skill blocks must have cache_control
        for block in payload["system"]:
            assert "cache_control" in block, f"Missing cache_control on block: {block}"

    def test_messages_has_user_turn(self):
        payload = build_cached_messages("sys", [], "hello world")
        msgs = payload["messages"]
        assert len(msgs) >= 1
        user_msg = msgs[0]
        assert user_msg["role"] == "user"
        # Content can be str or list
        if isinstance(user_msg["content"], str):
            assert "hello world" in user_msg["content"]
        else:
            text = " ".join(b.get("text", "") for b in user_msg["content"] if isinstance(b, dict))
            assert "hello world" in text

    def test_stable_content_precedes_volatile(self):
        """System blocks (stable) must appear before user message (volatile)."""
        payload = build_cached_messages("stable system", ["stable skill"], "volatile user")
        # system list is separate from messages list — that ordering is enforced structurally
        assert len(payload["system"]) >= 1
        assert payload["messages"][0]["role"] == "user"

    def test_empty_skills_still_works(self):
        payload = build_cached_messages("sys", [], "user")
        assert payload["system"][0]["text"] == "sys"

    def test_multiple_skills_produce_multiple_blocks(self):
        skills = ["alpha", "beta", "gamma"]
        payload = build_cached_messages("sys", skills, "user")
        # system list = 1 system prompt block + len(skills) skill blocks
        assert len(payload["system"]) == 1 + len(skills)
