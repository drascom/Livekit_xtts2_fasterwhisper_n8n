# AI Voice Agent - Development Plan

## Current State (Working Backend)

### agent.py - Core Components
- **LiveKit Agents SDK** with `AgentSession`
- **Custom Speech Client** (`speech_client.py`):
  - `DrascomSTT` - Speech-to-text via Speaches API
  - `DrascomTTS` - Text-to-speech via Speaches API
  - `SimpleEnergyVAD` - Voice activity detection
- **Ollama LLM** via LiveKit's OpenAI plugin (`openai.LLM.with_ollama()`)
- **MCP Integration** - n8n SSE server for tools (optional, `ENABLE_MCP=true`)
- **Language Detection** - Auto-switches between English/Turkish TTS voices
- **Console Mode** - `python3 agent.py console` for testing

### Environment Configuration
```
LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
OLLAMA_BASE_URL, OLLAMA_MODEL
SPEECH_SERVER_URL (STT/TTS)
N8N_MCP_SERVER_URL (for tools)
```

---

## Legacy System Features to Migrate

### Frontend (Next.js 14+)
| Feature | Description | Priority |
|---------|-------------|----------|
| WelcomeView | Pre-connection screen with "Start Call" button | High |
| SessionView | Active call with video tiles, chat, controls | High |
| AgentControlBar | Mic, camera, screen share, chat, disconnect | High |
| ChatTranscript | Real-time message display | High |
| SettingsModal | Voice, model, temperature config | Medium |
| ThemeProvider | Light/dark/system theme | Low |
| Audio Visualization | Shimmer text, audio levels | Low |

### Backend (Python)
| Feature | Description | Priority |
|---------|-------------|----------|
| Webhook Server | `/wake`, `/settings`, `/status` endpoints | High |
| Session Registry | Track active sessions per room | High |
| Settings Management | Persist/load agent config | Medium |
| Web Search | DuckDuckGo + Ollama summarization | Medium |
| n8n Workflows | Discover and execute workflows | High |
| Tool Caching | Cache last N tool responses | Medium |
| Model Preloading | Pre-warm STT/TTS/LLM on startup | Low |

### Integrations
| Integration | Description | Priority |
|-------------|-------------|----------|
| Home Assistant | Device control via MCP tools | High |
| n8n | Workflow automation | High |
| Ollama | Local LLM inference | High (done) |
| MCP Protocol | Extensible tool discovery | High (partial) |

---

## Architecture for Multi-User Support

### Current Limitation
Legacy uses single fixed room: `voice_assistant_room` - only one user at a time.

### Multi-User Solution

```
                    ┌─────────────────┐
                    │   LiveKit       │
                    │   Cloud/Server  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐
        │  Room A   │  │  Room B   │  │  Room C   │
        │  User 1   │  │  User 2   │  │  User 3   │
        │  Agent    │  │  Agent    │  │  Agent    │
        └───────────┘  └───────────┘  └───────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────┴────────┐
                    │  Agent Worker   │
                    │  (Dispatches)   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
   │ Ollama  │          │  n8n    │          │  Home   │
   │  LLM    │          │ Server  │          │Assistant│
   └─────────┘          └─────────┘          └─────────┘
```

**Key Changes:**
1. Dynamic room creation per user/session
2. Agent worker handles multiple concurrent rooms
3. Session-scoped context (each user has isolated conversation)
4. Shared backend services (Ollama, n8n, HA)

---

## Implementation Plan

### Phase 1: Backend Enhancements
1. **Webhook Server** (FastAPI)
   - `/api/token` - Generate LiveKit tokens with dynamic room names
   - `/api/status` - Agent health and model readiness
   - `/api/settings` - Get/set agent configuration
   - `/api/wake` - Trigger greeting for a specific room

2. **Session Management**
   - Room registry: `{room_name: (session, agent, user_info)}`
   - Auto-cleanup on disconnect
   - Per-session conversation history

3. **Enhanced MCP Integration**
   - Stable connection to n8n MCP server
   - Tool caching with TTL
   - Error recovery

### Phase 2: Frontend (Next.js)
1. **Core UI**
   - Landing page with "Start Call" button
   - Active session view with controls
   - Chat sidebar

2. **LiveKit Integration**
   - Token fetching via API
   - Room connection management
   - Audio/video rendering

3. **Settings Panel**
   - Voice selection
   - Model selection
   - Basic preferences

### Phase 3: Integrations
1. **n8n Workflows**
   - List available workflows
   - Execute with parameters
   - Handle responses

2. **Home Assistant**
   - Device discovery via MCP
   - Control actions (on/off, volume, etc.)

3. **Web Search**
   - DuckDuckGo integration
   - Ollama-based summarization

### Phase 4: Multi-User & Polish
1. **Concurrent Sessions**
   - Test with multiple simultaneous users
   - Resource management
   - Session isolation

2. **UI Refinements**
   - Theme support
   - Audio visualization
   - Connection status indicators

---

## File Structure (Proposed)

```
backend/
├── agent.py              # Main agent entrypoint (enhanced)
├── prompts.py            # System prompts
├── speech_client.py      # STT/TTS/VAD clients
├── tools.py              # Native tools
├── server.py             # API server (token, settings, webhooks)
├── session.py            # Session registry & management
├── settings.py           # Settings persistence
├── mcp_client/           # MCP integration
│   ├── __init__.py
│   ├── server.py
│   └── agent_tools.py
└── integrations/         # External service integrations
    ├── __init__.py
    ├── n8n.py            # n8n workflow client
    ├── web_search.py     # DuckDuckGo + summarization
    └── homeassistant.py  # HA control helpers

frontend/
├── app/
│   ├── page.tsx          # Landing page
│   ├── session/
│   │   └── page.tsx      # Active call view
│   ├── api/
│   │   ├── token/route.ts
│   │   ├── settings/route.ts
│   │   └── wake/route.ts
│   └── layout.tsx
├── components/
│   ├── WelcomeView.tsx
│   ├── SessionView.tsx
│   ├── ControlBar.tsx
│   ├── ChatPanel.tsx
│   └── SettingsModal.tsx
├── hooks/
│   ├── useAgent.ts
│   └── useSettings.ts
└── lib/
    ├── api.ts
    └── config.ts
```

---

## Tech Stack

### Backend
- Python 3.11+
- LiveKit Agents SDK
- FastAPI (webhooks/API)
- httpx (async HTTP)
- Ollama (LLM)
- Speaches (STT/TTS)

### Frontend
- Next.js 14+ (App Router)
- TypeScript
- Tailwind CSS
- LiveKit React SDK
- shadcn/ui components

### Infrastructure
- LiveKit Cloud or self-hosted
- Ollama server
- Speaches server
- n8n (optional)
- Home Assistant (optional)

---

## Next Steps

1. **Start with Phase 1** - Enhance backend with webhook server
2. **Create minimal frontend** - Just enough for testing
3. **Iterate** - Add features incrementally
4. **Test multi-user** - Verify isolation and concurrency

Ready to begin implementation when you give the go-ahead.
