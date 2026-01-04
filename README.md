# Geveze - AI Voice Assistant

Multi-user multimodal voice agent with Ollama, n8n, and Home Assistant integration.

## Quick Start

## Python Virtual Environment (uv)

Create the backend virtual environment and install dependencies:
```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Use the environment in new shells:
```bash
cd backend
source .venv/bin/activate
```

```bash
./start.sh
```

This starts both backend and frontend. Open http://localhost:3000

## Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
source .venv/bin/activate
python3 agent.py dev
```

**Terminal 2 - Frontend:**
```bash
cd frontend
pnpm dev
```



## URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8889 |
| API Docs | http://localhost:8889/docs |

## Configuration

### Backend (`backend/.env`)
```
LIVEKIT_URL=wss://your-livekit-server
LIVEKIT_API_KEY=your-key
LIVEKIT_API_SECRET=your-secret
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=ministral-3:8b
SPEECH_SERVER_URL=https://your-speech-server
```

### Frontend (`frontend/.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8889
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│  API Server │────▶│  LiveKit    │
│  (Next.js)  │     │  (FastAPI)  │     │  Agent      │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌─────────┐  ┌─────────┐
        │ Ollama  │  │  n8n    │  │  Home   │
        │  LLM    │  │ Server  │  │Assistant│
        └─────────┘  └─────────┘  └─────────┘
```

## Features

- Real-time voice conversation
- Multi-language support (English/Turkish)
- MCP tool integration
- Session management
- Settings persistence
