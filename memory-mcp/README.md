# Local Memory MCP Server

Lightweight MCP server that stores key/value pairs in a JSON file inside the repo. Useful as a “memory” provider for the Codex VS Code extension or other MCP clients.

## Setup
```
cd memory-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```
python3 server.py
```
Defaults:
- Host: `127.0.0.1`
- Port: `3001`
- Store file: `memory-mcp/memory.json`

Configure via env vars: `MEMORY_MCP_HOST`, `MEMORY_MCP_PORT`, `MEMORY_MCP_STORE`, `MEMORY_MCP_LOG_LEVEL`.

## Wire into Codex / MCP clients
Add to `mcp_servers.json` at the repo root:
```json
{
  "servers": [
    {
      "name": "memory",
      "url": "http://localhost:3001/mcp",
      "transport": "streamable_http"
    }
  ]
}
```
Reload the Codex extension; the tools will appear as `memory_save`, `memory_get`, `memory_delete`, and `memory_list`.
