"""FastAPI server for voice agent API endpoints."""

from __future__ import annotations

import os
import random
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel

load_dotenv()

# LiveKit imports
from livekit import api as livekit_api
from livekit.api import LiveKitAPI, ListRoomsRequest

# Local imports
from session import registry
from settings import settings_manager

# Environment variables
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")
SPEECH_SERVER_URL = os.environ.get("SPEECH_SERVER_URL", "")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama.drscom.uk")


# Pydantic models for API
class TokenRequest(BaseModel):
    """Request for generating a LiveKit token."""
    user_name: str = "User"
    room_name: Optional[str] = None


class TokenResponse(BaseModel):
    """Response containing LiveKit connection details."""
    token: str
    room_name: str
    livekit_url: str
    user_identity: str


class SettingsUpdate(BaseModel):
    """Request for updating agent settings."""
    agent_name: Optional[str] = None
    tts_voice: Optional[str] = None
    tts_voice_tr: Optional[str] = None
    llm_model: Optional[str] = None
    temperature: Optional[float] = None
    num_ctx: Optional[int] = None
    max_turns: Optional[int] = None
    prompt_mode: Optional[str] = None
    custom_prompt: Optional[str] = None
    enable_mcp: Optional[bool] = None
    enable_web_search: Optional[bool] = None


class WakeRequest(BaseModel):
    """Request to wake/greet in a specific room."""
    room_name: str
    message: Optional[str] = None


class StatusResponse(BaseModel):
    """Agent status response."""
    status: str
    agent_ready: bool
    active_sessions: int
    livekit_connected: bool
    speech_server_available: bool


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print("API server starting...")
    yield
    # Shutdown
    print("API server shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Geveze Voice Agent API",
    description="API for managing voice agent sessions and settings",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper functions
async def get_existing_rooms() -> List[str]:
    """Get list of existing room names from LiveKit."""
    try:
        lk_api = LiveKitAPI()
        rooms = await lk_api.room.list_rooms(ListRoomsRequest())
        await lk_api.aclose()
        return [room.name for room in rooms.rooms]
    except Exception:
        return []


async def generate_unique_room_name() -> str:
    """Generate a unique room name."""
    existing = await get_existing_rooms()
    while True:
        name = f"room-{uuid.uuid4().hex[:8]}"
        if name not in existing:
            return name


def generate_token(room_name: str, user_identity: str, user_name: str) -> str:
    """Generate a LiveKit access token."""
    token = livekit_api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token = token.with_identity(user_identity)
    token = token.with_name(user_name)
    token = token.with_grants(
        livekit_api.VideoGrants(
            room_join=True,
            room=room_name,
        )
    )
    return token.to_jwt()


def _ollama_api_base(url: str) -> str:
    cleaned = url.rstrip("/")
    if cleaned.endswith("/v1"):
        return cleaned[:-3]
    return cleaned


# API Routes
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": registry.active_count,
    }


@app.get("/api/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Get agent status and readiness."""
    # Check LiveKit connection
    livekit_connected = bool(LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET)

    # Check speech server (basic check)
    speech_available = bool(SPEECH_SERVER_URL)

    return StatusResponse(
        status="ready" if livekit_connected else "not_configured",
        agent_ready=livekit_connected and speech_available,
        active_sessions=registry.active_count,
        livekit_connected=livekit_connected,
        speech_server_available=speech_available,
    )


@app.post("/api/token", response_model=TokenResponse)
async def create_token(request: TokenRequest) -> TokenResponse:
    """Generate a LiveKit token for joining a room."""
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(status_code=500, detail="LiveKit not configured")

    # Generate or use provided room name
    room_name = request.room_name or await generate_unique_room_name()

    # Generate unique user identity
    user_identity = f"user-{uuid.uuid4().hex[:8]}"

    # Generate token
    token = generate_token(room_name, user_identity, request.user_name)

    return TokenResponse(
        token=token,
        room_name=room_name,
        livekit_url=LIVEKIT_URL,
        user_identity=user_identity,
    )


@app.get("/api/sessions")
async def list_sessions() -> Dict[str, Any]:
    """List all active sessions."""
    return registry.to_dict()


@app.get("/api/settings")
async def get_settings() -> Dict[str, Any]:
    """Get current agent settings."""
    return settings_manager.settings.to_dict()


@app.post("/api/settings")
async def update_settings(update: SettingsUpdate) -> Dict[str, Any]:
    """Update agent settings."""
    # Filter out None values
    updates = {k: v for k, v in update.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No settings to update")

    settings_manager.update(**updates)
    return settings_manager.settings.to_dict()


@app.post("/api/settings/reset")
async def reset_settings() -> Dict[str, Any]:
    """Reset settings to defaults."""
    settings_manager.reset()
    return settings_manager.settings.to_dict()


@app.post("/api/wake")
async def wake_agent(request: WakeRequest) -> Dict[str, str]:
    """
    Trigger agent greeting in a specific room.
    The agent will speak the provided message or a random greeting.
    """
    session = registry.get(request.room_name)

    if not session:
        raise HTTPException(status_code=404, detail=f"No active session in room '{request.room_name}'")

    if not session.agent_session:
        raise HTTPException(status_code=400, detail="Agent session not available")

    # Get message to speak
    message = request.message
    if not message:
        greetings = settings_manager.settings.wake_greetings
        message = random.choice(greetings)

    # Generate reply through agent session
    try:
        await session.agent_session.generate_reply(instructions=message)
        return {"status": "ok", "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/voices")
async def list_voices() -> List[Dict[str, str]]:
    """List available TTS voices."""
    # These are the voices configured in the system
    # In a full implementation, this would query the speech server
    return [
        {"id": "jenny_dioco", "name": "Jenny (English)", "language": "en"},
        {"id": "fahrettin", "name": "Fahrettin (Turkish)", "language": "tr"},
    ]


@app.get("/api/models")
async def list_models() -> List[Dict[str, str]]:
    """List available LLM models."""
    base_url = _ollama_api_base(OLLAMA_BASE_URL)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
        models = data.get("models", [])
        return [{"id": model.get("name", ""), "name": model.get("name", "")} for model in models if model.get("name")]
    except Exception:
        return [
            {"id": "ministral-3:8b", "name": "Ministral 3B"},
            {"id": "qwen3:8b", "name": "Qwen 3 8B"},
            {"id": "llama3.2:3b", "name": "Llama 3.2 3B"},
            {"id": "gemma2:2b", "name": "Gemma 2 2B"},
        ]


@app.get("/api/rooms")
async def list_rooms() -> List[str]:
    """List active LiveKit rooms."""
    return await get_existing_rooms()


# Run with: uvicorn api:app --host 0.0.0.0 --port 8889 --reload
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8889)
