"""AgentSpec — declarative configuration for a SkyHerd managed agent session.

Each field maps directly to how the agent is wired in AgentMesh:
- ``system_prompt_template_path``: path to a Markdown file whose content
  becomes the ``system_prompt`` block sent with ``cache_control``.
- ``wake_topics``: MQTT wildcard topics that trigger ``SessionManager.wake()``.
- ``mcp_servers``: logical MCP server names; resolved to real configs by
  ``AgentMesh`` at startup.
- ``skills``: paths to skill ``.md`` files; loaded at wake time and sent as
  additional ``cache_control`` blocks so they count as cached input tokens.
- ``checkpoint_interval_s``: how often to serialise session state to disk.
- ``max_idle_s_before_checkpoint``: force a checkpoint after this many idle seconds.
- ``model``: Anthropic model string. Defaults to claude-opus-4-7.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_DEFAULT_MODEL = "claude-opus-4-7"


@dataclass
class AgentSpec:
    """Declarative specification for a single SkyHerd agent session.

    Attributes
    ----------
    name:
        Human-readable name; used as the session directory name and log prefix.
    system_prompt_template_path:
        Path to a Markdown file that becomes the first ``cache_control`` block.
    wake_topics:
        MQTT topic patterns (MQTT wildcards ``+`` and ``#`` supported).
    mcp_servers:
        Logical MCP server names (``"drone_mcp"``, ``"sensor_mcp"``, …).
    skills:
        Paths to skill ``.md`` files loaded at wake-cycle start.
    checkpoint_interval_s:
        Periodic checkpoint interval in seconds. 0 disables.
    max_idle_s_before_checkpoint:
        Checkpoint after this many consecutive idle seconds. 0 disables.
    model:
        Anthropic model string; defaults to ``claude-opus-4-7``.
    """

    name: str
    system_prompt_template_path: str
    wake_topics: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    checkpoint_interval_s: int = 3600
    max_idle_s_before_checkpoint: int = 300
    model: str = _DEFAULT_MODEL
