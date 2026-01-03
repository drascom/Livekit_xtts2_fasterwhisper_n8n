# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

```bash
# Start all services (foreground)
docker compose up --build

# Start all services (background)
docker compose up --build -d

# Stop all services
docker compose down

# Frontend development (outside Docker)
cd frontend && pnpm install && pnpm dev

# Run tests
python3 -m venv .venv-test && source .venv-test/bin/activate && pip install -r tests/requirements.txt
pytest tests/ -v              # All tests
pytest tests/ -m stt -v       # STT only
pytest tests/ -m tts -v       # TTS only
pytest tests/ -m "not slow" -v  # Skip slow tests
./tests/run_tests.sh [stt|tts|quick]
```

## Architecture Overview

This is **Geveze** - a voice assistant microservices platform enabling real-time voice conversations via LiveKit, Ollama LLM, and n8n workflow integrations.

### Data Flow

```
Browser → Frontend (Next.js :3000) → LiveKit Server (:7880)
                                          ↓
                                    Voice Agent (:8889)
                                    ├─→ STT (Speaches :8000)
                                    ├─→ Ollama LLM → Tool Execution (n8n/MCP)
                                    └─→ TTS (XTTS :8003)
```

### Services

| Service | Port | Location | Purpose |
|---------|------|----------|---------|
| frontend | 3000 | `/frontend` | Next.js UI, LiveKit token generation, settings UI |
| voice-agent | 8889 | `/voice-agent` | Main Python agent: STT→LLM→TTS pipeline, tool orchestration |
| stt-service | 8000 | External container | Speaches (Faster-Whisper), OpenAI-compatible |
| tts-service | 8003 | `/tts-service` | Coqui XTTS v2, OpenAI-compatible |
| livekit | 7880 | `/livekit` | LiveKit media server |

### Key Voice Agent Components

- **`voice_agent.py`**: Main entrypoint, agent lifecycle, session management
- **`llm/ollama_llm.py`**: Custom LiveKit LLM plugin supporting Qwen3's think parameter
- **`llm/ollama_node.py`**: Custom LLM node bypassing LiveKit's standard wrapper
- **`integrations/n8n.py`**: Discovers n8n workflows via MCP, exposes as LLM tools
- **`integrations/mcp_loader.py`**: Loads MCP server configurations
- **`webhooks.py`**: FastAPI endpoints (`/announce`, `/wake`, `/reload-tools`, `/settings`, `/voices`, `/models`)
- **`settings.py`**: Runtime-configurable settings persisted to `settings.json`
- **`session_registry.py`**: Maps room names to active AgentSession instances
- **`agent_status.py`**: Tracks STT/TTS/LLM model readiness

### Frontend Key Files

- **`app/api/connection-details/route.ts`**: LiveKit token generation
- **`app/api/settings/route.ts`**: Proxies to voice-agent settings
- **`hooks/useStartupStatus.tsx`**: Polls model readiness status
- **`components/agent-controls/`**: Settings UI components

## Configuration

All services share a single `.env` file at repo root. Key variables:

- **LiveKit**: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- **STT**: `SPEACHES_URL`, `WHISPER_MODEL`
- **TTS**: `TTS_SERVICE_URL`, `XTTS_DEFAULT_VOICE`, `XTTS_DEFAULT_LANGUAGE`
- **LLM**: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_THINK`, `OLLAMA_TEMPERATURE`, `OLLAMA_NUM_CTX`
- **n8n**: `N8N_BASE_URL`, `N8N_MCP_URL`, `N8N_MCP_TOKEN`

## n8n Workflow Integration

Workflows in `/n8n-workflows` are discovered via MCP and exposed as LLM tools.

```bash
cd n8n-workflows
cp config.env.example config.env
python setup.py  # Creates workflows in n8n
```

Workflow naming convention: `service_action_object` (e.g., `calendar_get_events`).

## Technical Notes

- STT and TTS use OpenAI-compatible API interfaces
- Custom Ollama LLM node exists to support Qwen3's `think` parameter for reasoning
- Tool results are cached to prevent redundant executions
- Settings are hot-reloadable at runtime via JSON file
- All services communicate over Docker network `geveze-network`
- GPU support (NVIDIA) required for STT and TTS services
