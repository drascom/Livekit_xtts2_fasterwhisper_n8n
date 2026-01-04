"""
MCP integrations for voice assistant.
"""

from .mcp_loader import load_mcp_config, initialize_mcp_servers, MCPServerConfig
from .n8n import discover_n8n_workflows, execute_n8n_workflow
from .web_search import WebSearchTools

__all__ = [
    "load_mcp_config",
    "initialize_mcp_servers",
    "MCPServerConfig",
    "discover_n8n_workflows",
    "execute_n8n_workflow",
    "WebSearchTools",
]
