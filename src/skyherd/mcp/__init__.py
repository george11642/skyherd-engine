"""
SkyHerd MCP servers — drone, sensor, rancher, and galileo tool suites.

Each server factory returns a ``McpSdkServerConfig`` suitable for
``ClaudeAgentOptions.mcp_servers``.  Import only what you need; every
module is safe to import in isolation with no side effects.
"""

from skyherd.mcp.drone_mcp import create_drone_mcp_server
from skyherd.mcp.galileo_mcp import create_galileo_mcp_server
from skyherd.mcp.rancher_mcp import create_rancher_mcp_server
from skyherd.mcp.sensor_mcp import create_sensor_mcp_server

__all__ = [
    "create_drone_mcp_server",
    "create_sensor_mcp_server",
    "create_rancher_mcp_server",
    "create_galileo_mcp_server",
]
