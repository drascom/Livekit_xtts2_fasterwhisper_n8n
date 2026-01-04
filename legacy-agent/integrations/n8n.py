"""n8n workflow discovery and tool wrapping.

Convention:
- All workflows use webhook triggers
- Webhook URL = http://HOST:PORT/webhook/{workflow_name}
- Workflow descriptions in webhook node notes document expected parameters
"""

import json
import logging
import time
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Cache for workflow details to avoid redundant MCP calls
_workflow_details_cache: dict[str, dict] = {}
_cache_timestamp: float = 0
_cache_ttl_seconds: float = 3600  # 1 hour TTL


async def discover_n8n_workflows(n8n_mcp, base_url: str) -> tuple[list[dict], dict[str, str]]:
    """Discover n8n workflows and create tool definitions.

    Convention: All workflows use webhook triggers with webhook path = workflow name.
    Workflow descriptions extracted from webhook node notes.

    Args:
        n8n_mcp: Initialized n8n MCP server client
        base_url: n8n base URL (e.g. http://192.168.1.100:5678)

    Returns:
        Tuple of (ollama_tools, workflow_name_map)
        - ollama_tools: List of tool dicts in Ollama format
        - workflow_name_map: Dict mapping tool_name -> workflow_name
    """
    tools = []
    workflow_name_map = {}

    # Check cache expiry
    current_time = time.time()
    global _cache_timestamp, _workflow_details_cache
    if current_time - _cache_timestamp > _cache_ttl_seconds:
        _workflow_details_cache.clear()
        _cache_timestamp = current_time
        logger.debug("Cleared workflow details cache (TTL expired)")

    try:
        # Get list of workflows (basic info only)
        result = await n8n_mcp._client.call_tool("search_workflows", {})
        workflows_data = parse_mcp_result(result)

        # n8n returns {"data": [...], "count": N}
        if isinstance(workflows_data, dict) and "data" in workflows_data:
            workflows = workflows_data["data"]
        else:
            logger.warning(f"Unexpected workflows format: {type(workflows_data)}")
            workflows = []

        logger.info(f"Loading {len(workflows)} n8n workflows:")

        for workflow in workflows:
            wf_name = workflow["name"]  # Original workflow name
            wf_id = workflow["id"]  # Need ID for get_workflow_details
            tool_name = sanitize_tool_name(wf_name)

            # Try to get detailed description from webhook notes
            description = ""
            try:
                # Check cache first
                if wf_id not in _workflow_details_cache:
                    details_result = await n8n_mcp._client.call_tool(
                        "get_workflow_details",
                        {"workflowId": wf_id}
                    )
                    _workflow_details_cache[wf_id] = parse_mcp_result(details_result)

                workflow_details = _workflow_details_cache[wf_id]
                description = extract_webhook_description(workflow_details)

            except Exception as e:
                logger.warning(f"Failed to get details for {wf_name}: {e}")

            # Fallback to root description or generic message
            if not description:
                description = workflow.get("description") or f"Execute {tool_name} workflow"

            # Flexible schema - LLM uses description to determine parameters
            parameters = {
                "type": "object",
                "additionalProperties": True  # Accept any properties
            }

            # Create Ollama tool definition
            tool = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": description,
                    "parameters": parameters,
                },
            }
            tools.append(tool)
            workflow_name_map[tool_name] = wf_name  # Map sanitized -> original name
            logger.info(f"  ✓ {tool_name}")

    except Exception as e:
        logger.warning(f"Failed to discover n8n workflows: {e}", exc_info=True)
    return tools, workflow_name_map


async def execute_n8n_workflow(base_url: str, workflow_name: str, arguments: dict) -> Any:
    """Execute an n8n workflow via POST request.

    Convention: webhook URL = {base_url}/webhook/{workflow_name}

    Args:
        base_url: n8n base URL (e.g. http://192.168.1.100:5678)
        workflow_name: The workflow name (used in webhook path)
        arguments: Arguments to pass to the workflow as JSON body

    Returns:
        Workflow execution result (only final node output)
    """
    webhook_url = f"{base_url.rstrip('/')}/webhook/{workflow_name}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(webhook_url, json=arguments) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Failed to execute n8n workflow {workflow_name}: {e}")
            raise


def extract_webhook_description(workflow_details: dict) -> str:
    """Extract description from webhook node notes.

    Searches for webhook trigger node and extracts its notes field,
    which contains the workflow description and parameter documentation.

    Args:
        workflow_details: Full workflow structure from get_workflow_details MCP call

    Returns:
        Description string for CAAL tool discovery, or empty string if not found
    """
    # Find webhook node in workflow
    for node in workflow_details.get("workflow", {}).get("nodes", []):
        if node.get("type") == "n8n-nodes-base.webhook":
            # Extract notes field
            notes = node.get("notes", "").strip()
            if notes:
                return notes

            # Fallback: use node description if available
            node_desc = node.get("description", "").strip()
            if node_desc:
                return node_desc

    return ""


def sanitize_tool_name(name: str) -> str:
    """Convert workflow name to valid tool name (lowercase, underscores)."""
    return name.lower().replace(" ", "_").replace("-", "_")


def clear_caches() -> None:
    """Clear all n8n workflow caches for hot reload.

    Call this before re-discovering workflows to ensure fresh data.
    """
    global _workflow_details_cache, _cache_timestamp
    _workflow_details_cache.clear()
    _cache_timestamp = 0
    logger.info("Cleared n8n workflow caches")


def parse_mcp_result(result) -> Any:
    """Parse MCP tool result, extracting content."""
    # Handle different MCP response formats
    if hasattr(result, "content") and result.content:
        # Get the first content item
        content_item = result.content[0]

        # Extract text from content
        text = content_item.text if hasattr(content_item, "text") else str(content_item)

        # Try to parse as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # If not JSON, return as-is
            return text

    # Fallback: return result as-is
    return result
