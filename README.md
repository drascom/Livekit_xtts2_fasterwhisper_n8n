# Geveze Microservices

Decoupled voice assistant backend for the Geveze stack. This project runs the
services on the same Docker host behind an HTTPS reverse proxy.

## Services

- **voice-agent**: LiveKit Agents worker + webhooks (wake, greeting, query)
- **stt-service**: speech-to-text (currently stubbed)
- **tts-service**: text-to-speech (currently stubbed)

## Single Environment File

All services and the frontend read from one shared file at the repo root:

```
/Users/drascom/Work Folder/geveze/.env
```

Then fill in your real values:

```
LIVEKIT_URL=wss://livekit.geveze.drascom.uk:7443
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

OLLAMA_BASE_URL=https://ollama.drascom.uk
N8N_BASE_URL=https://n8n.drascom.uk
N8N_MCP_URL=https://n8n.drascom.uk/mcp-server/http
N8N_MCP_TOKEN=your_n8n_mcp_token_here

CAAL_BRIDGE_URL=https://geveze.drascom.uk
WEBHOOK_URL=http://voice-agent:8889
```

## Frontend

The frontend lives in `frontend` and generates LiveKit tokens locally.

```
cd frontend
pnpm install
pnpm dev
```

The frontend reads `.env` through the API route `/api/connection-details`.

## Reverse Proxy / Domains

Recommended public endpoints:

- UI: `https://geveze.drascom.uk` (Nginx Proxy Manager hosts the React UI)
- LiveKit WSS: `wss://livekit.drascom.uk` (proxied to `http://192.168.0.252:7880`, use port 7443/SSL on the proxy)
- Ollama: `https://ollama.drascom.uk` (remote)
- n8n: `https://n8n.drascom.uk` (remote)

## Notes

- STT and TTS are placeholders and should be replaced with real engines.
- voice-agent exposes `/wake`, `/agent/greeting`, and `/agent/query`.


  Running Tests Later

  # Create virtual environment (if not exists)
  python3 -m venv .venv-test
  source .venv-test/bin/activate
  pip install -r tests/requirements.txt

  # Run all tests
  pytest tests/ -v

  # Run only STT tests
  pytest tests/ -m stt -v

  # Run only TTS tests
  pytest tests/ -m tts -v

  # Run quick tests (skip slow TTS generation)
  pytest tests/ -m "not slow" -v

  # Or use the runner script
  ./tests/run_tests.sh          # All tests
  ./tests/run_tests.sh stt      # STT only
  ./tests/run_tests.sh tts      # TTS only
  ./tests/run_tests.sh quick    # Skip slow tests

  Note: The quick tests (20 tests) all pass. The slow TTS tests are failing with 500 errors - you may want to check the TTS service logs (docker logs geveze-tts-service-1) as the XTTS model may have resource issues.