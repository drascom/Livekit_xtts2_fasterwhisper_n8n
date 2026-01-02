#!/usr/bin/env python3
"""
Local JSON-backed memory MCP server.

Run with:
    python3 memory-mcp/server.py

Configuration (env vars):
    MEMORY_MCP_PORT   - Port to listen on (default: 3001)
    MEMORY_MCP_HOST   - Host interface (default: 127.0.0.1)
    MEMORY_MCP_STORE  - Path to JSON store file (default: memory-mcp/memory.json)
    MEMORY_MCP_LOG_LEVEL - Log level (DEBUG/INFO/WARNING/ERROR, default: INFO)
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from mcp.server.fastmcp import Context, FastMCP


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_STORE = Path(__file__).parent / "memory.json"
STORE_PATH = Path(os.getenv("MEMORY_MCP_STORE", DEFAULT_STORE))
STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

HOST = os.getenv("MEMORY_MCP_HOST", "127.0.0.1")
PORT = int(os.getenv("MEMORY_MCP_PORT", "3001"))
LOG_LEVEL = os.getenv("MEMORY_MCP_LOG_LEVEL", "INFO")

_write_lock = asyncio.Lock()

mcp = FastMCP(
    name="local-memory",
    instructions="Lightweight JSON memory for Codex/VS Code.",
    host=HOST,
    port=PORT,
    log_level=LOG_LEVEL,
    json_response=True,
)


# =============================================================================
# Storage helpers
# =============================================================================

def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_store() -> dict[str, dict[str, Any]]:
    if not STORE_PATH.exists():
        return {}

    try:
        with STORE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"Failed to read memory store, starting fresh: {exc}")
    return {}


def _write_store(data: dict[str, dict[str, Any]]) -> None:
    tmp_path = STORE_PATH.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp_path.replace(STORE_PATH)


async def _save_entry(key: str, value: str) -> dict[str, Any]:
    async with _write_lock:
        data = _load_store()
        entry = {"value": value, "updated_at": _timestamp()}
        data[key] = entry
        _write_store(data)
        return {"key": key, **entry}


# =============================================================================
# MCP tools
# =============================================================================

@mcp.tool(name="memory_save", description="Store or overwrite a value in local memory.")
async def memory_save(key: str, value: str, ctx: Context | None = None) -> dict[str, Any]:
    """Persist a key/value pair to the local JSON store."""
    result = await _save_entry(key, value)
    if ctx:
        await ctx.info(f"Saved '{key}'")
    return result


@mcp.tool(name="memory_get", description="Retrieve a value from local memory.")
async def memory_get(key: str, ctx: Context | None = None) -> dict[str, Any]:
    """Get a value and metadata for a given key."""
    data = _load_store()
    if key not in data:
        raise ValueError(f"No entry found for key '{key}'")
    if ctx:
        await ctx.debug(f"Loaded '{key}'")
    return {"key": key, **data[key]}


@mcp.tool(name="memory_delete", description="Remove a key from local memory.")
async def memory_delete(key: str, ctx: Context | None = None) -> dict[str, Any]:
    """Delete a stored value."""
    async with _write_lock:
        data = _load_store()
        entry = data.pop(key, None)
        if entry is None:
            raise ValueError(f"No entry found for key '{key}'")
        _write_store(data)
    if ctx:
        await ctx.info(f"Deleted '{key}'")
    return {"key": key, "status": "deleted"}


@mcp.tool(name="memory_list", description="List stored keys with timestamps.")
async def memory_list(prefix: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """
    List stored entries, optionally filtered by prefix.

    Args:
        prefix: Optional key prefix filter.
        limit: Maximum number of entries to return (sorted by last update).
    """
    data = _load_store()
    items = []
    for key, entry in data.items():
        if prefix and not key.startswith(prefix):
            continue
        items.append({"key": key, **entry})

    items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return items[:limit]


# =============================================================================
# Entrypoint
# =============================================================================

if __name__ == "__main__":
    logger.info(f"Starting local-memory MCP server on {HOST}:{PORT}")
    logger.info(f"Store file: {STORE_PATH}")
    mcp.run(transport="streamable-http")
