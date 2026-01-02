# CAAL (Conversational AI Agent) System Workflow

The CAAL project implements a voice assistant system built around the **LiveKit Agent** framework, orchestrating a LiveKit frontend, a self-hosted LLM (Ollama), and n8n for external integrations.

### 1. Frontend (Mobile Client) - Flutter Application

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Connectivity** | LiveKit Client (`livekit_client`) | Connects to the CAAL Server's `/api/connection-details` endpoint to obtain a LiveKit token and join a room, establishing a bidirectional media and data channel. |
| **Initiation** | Porcupine (`porcupine_flutter`) | **On-device wake-word detection** using [`assets/wakeword.ppn`](mobile/assets/wakeword.ppn). Upon detection, the client performs two critical actions: 1) Posts to the CAAL Server's `/api/wake` endpoint to initiate a server-side action (e.g., a greeting/session start). 2) **Unmutes its LiveKit microphone track** to begin streaming the user's speech to the server. |
| **Input** | LiveKit Audio/Data | User's voice is streamed to the LiveKit server via the now-unmuted audio track. Text messages are sent via a LiveKit Data Channel. |

### 2. LiveKit Agent (Backend) - Python Service

The LiveKit Agent is the central orchestration point for voice processing, intelligence, and tool execution.

| Step | Component | Action |
| :--- | :--- | :--- |
| **LiveKit Ingestion** | LiveKit Agent Framework | Receives the mobile client's audio stream. |
| **Speech-to-Text (STT)** | LiveKit Agent Framework | Converts the received audio stream into text, which is provided to the LLM as a `ChatContext` message. (Component inferred from framework usage). |
| **LLM & Tool Selection** | Custom LLM Node (`ollama_llm_node()`) | This core function overrides the standard LLM behavior. It uses the **Ollama** Python library to query a local LLM (e.g., Qwen3). It first calls the LLM with the user's transcribed text and a list of available tools to determine if a function call is required. |
| **Tool Discovery** | `_discover_tools()` / `src/caal/integrations/n8n.py` | Tools are aggregated from three sources: **1. Agent-local methods** (`@function_tool` decorated). **2. Other configured MCP Servers**. **3. n8n Workflows** (discovered via an n8n MCP server and exposed as LLM tools). |
| **Tool Execution** | `_execute_single_tool()` | **Routing Priority:** Agent Method > n8n Workflow > Other MCP Tools. n8n workflows are executed by an HTTP POST request to the corresponding n8n Webhook URL, with the LLM-generated arguments as the JSON body. |
| **Final LLM Response** | Custom LLM Node | If a tool was executed, the LLM is called a second time with the tool's result injected into the chat context. It streams the final, natural language response text. |
| **Text-to-Speech (TTS)** | LiveKit Agent Framework | Converts the final LLM text response back into an audio stream. (Component inferred from framework usage). |

### API Routes (Frontend → Voice Agent)

All voice agent API calls are proxied through Next.js API routes to avoid CORS issues when running in Docker:

| Frontend Path | Voice Agent Endpoint | Purpose |
|--------------|---------------------|---------|
| `/api/wake` | `POST /wake` | Wake agent with greeting |
| `/api/settings` | `GET/POST /settings` | Get/update agent settings |
| `/api/voices` | `GET /voices` | List available TTS voices |
| `/api/models` | `GET /models` | List available LLM models |
| `/api/connection-details` | N/A | Generate LiveKit token |

The `WEBHOOK_URL` environment variable (default: `http://voice-agent:8889`) configures which voice agent the frontend proxies to.

### 3. Output Flow

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Audio Output** | LiveKit Agent to Mobile Client | The TTS-generated audio stream is sent back to the mobile client via LiveKit. |
| **Text/Visuals** | LiveKit Data Channel | Transcription, tool usage status, and other non-audio data are sent back to the client. The mobile app renders this as a real-time transcription or visualizer view. |

## Workflow Diagram

```mermaid
graph TD
    subgraph Frontend: Mobile Client (Flutter)
        A[Start] --> B(Porcupine Wake Word Detected);
        B --> C[POST /api/wake];
        B --> D[Unmute LiveKit Mic];
        D --> E[LiveKit Audio Stream];
    end

    subgraph Backend: LiveKit Agent (Python)
        E --> F[LiveKit Ingestion];
        F --> G(Speech-to-Text: STT);
        G --> H{LLM: Tool Call Required?};
        H -- Yes --> I(Tool Execution: n8n/MCP/Local);
        I --> H;
        H -- No / Complete --> J(LLM: Final Response Generation);
        J --> K(Text-to-Speech: TTS);
        K --> L[LiveKit Audio Response Stream];
    end
    
    subgraph Tool Integrations
        C --> M(Server-side Wake Action);
        I --> N[n8n Webhook POST]
        I --> O[Other MCP Tool Call]
    end

    L --> P[LiveKit Audio Output];
    H --> Q[LiveKit Data Channel: Status/Text];
    Q --> R[Mobile App UI Update];

    P --> R;
    R --> S[End User Experience];
```