"""Webhook server for external triggers (announcements, tool reload, wake word, settings).

This module provides HTTP endpoints that allow external systems (like n8n)
and the frontend to trigger actions on the running voice agent.

Endpoints:
    POST /announce      - Make the agent speak a message
    POST /reload-tools  - Refresh MCP tool cache and optionally announce
    POST /wake          - Handle wake word detection (greet user)
    GET  /health        - Health check
    GET  /settings      - Get current settings
    POST /settings      - Update settings
    GET  /prompt        - Get current prompt content
    POST /prompt        - Save custom prompt
    GET  /voices        - List available TTS voices
    GET  /models        - List available LLM models

Usage:
    # Start in a background thread from voice_agent.py:
    import threading
    import uvicorn
    from caal.webhooks import app

    def run_webhook_server():
        uvicorn.run(app, host="0.0.0.0", port=8889, log_level="info")

    webhook_thread = threading.Thread(target=run_webhook_server, daemon=True)
    webhook_thread.start()
"""

from __future__ import annotations

import logging
import os
import random

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import settings as settings_module
import session_registry
from agent_status import get_status_snapshot
from llm.ollama_node import ToolDataCache, ollama_llm_node
from livekit.agents.llm import ChatContext

if os.getenv("OLLAMA_BASE_URL"):
    os.environ["OLLAMA_HOST"] = os.getenv("OLLAMA_BASE_URL")

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CAAL Webhook API",
    description="External triggers for CAAL voice agent",
    version="1.0.0",
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Frontend can be on different port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TIMEZONE_ID = os.getenv("TIMEZONE", "America/Los_Angeles")
TIMEZONE_DISPLAY = os.getenv("TIMEZONE_DISPLAY", "Pacific Time")
OLLAMA_THINK = os.getenv("OLLAMA_THINK", "false").lower() == "true"
TTS_SERVICE_URL = os.getenv("TTS_SERVICE_URL", "http://tts-service:8003")
TTS_URL = os.getenv("TTS_URL", f"{TTS_SERVICE_URL}/tts/synthesize")
TTS_VOICES_ENDPOINT = f"{TTS_SERVICE_URL}/v1/audio/voices"

_history_cache: dict[str, ChatContext] = {}
_tool_data_cache_map: dict[str, ToolDataCache] = {}


class AnnounceRequest(BaseModel):
    """Request body for /announce endpoint."""

    message: str
    room_name: str = "voice_assistant_room"


class ReloadToolsRequest(BaseModel):
    """Request body for /reload-tools endpoint."""

    tool_name: str | None = None  # Optional: announce specific tool name
    message: str | None = None  # Optional: custom announcement message (overrides tool_name)
    room_name: str = "voice_assistant_room"


class WakeRequest(BaseModel):
    """Request body for /wake endpoint."""

    room_name: str = "voice_assistant_room"


class WakeResponse(BaseModel):
    """Response body for /wake endpoint."""

    status: str
    room_name: str


class AnnounceResponse(BaseModel):
    """Response body for /announce endpoint."""

    status: str
    room_name: str


class ReloadToolsResponse(BaseModel):
    """Response body for /reload-tools endpoint."""

    status: str
    tool_count: int
    room_name: str


class HealthResponse(BaseModel):
    """Response body for /health endpoint."""

    status: str
    active_sessions: list[str]


class AgentStatusResponse(BaseModel):
    """Response body for /status endpoint."""

    ready: bool
    message: str | None
    models: dict[str, dict[str, object]]
    timestamp: float


class GreetingRequest(BaseModel):
    """Request body for /agent/greeting endpoint."""

    instruction: str | None = None
    room_name: str = "voice_assistant_room"


class GreetingResponse(BaseModel):
    """Response body for /agent/greeting endpoint."""

    text: str
    audio_url: str


class AgentQueryRequest(BaseModel):
    """Request body for /agent/query endpoint."""

    transcript: str
    room_name: str


class AgentQueryResponse(BaseModel):
    """Response body for /agent/query endpoint."""

    response_text: str
    response_audio_url: str


def _get_runtime_settings() -> dict:
    settings = settings_module.load_settings()
    return {
        "model": settings.get("model") or os.getenv("OLLAMA_MODEL", "ministral-3:8b"),
        "temperature": settings.get("temperature", float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))),
        "num_ctx": settings.get("num_ctx", int(os.getenv("OLLAMA_NUM_CTX", "8192"))),
        "max_turns": settings.get("max_turns", int(os.getenv("OLLAMA_MAX_TURNS", "20"))),
        "tool_cache_size": settings.get("tool_cache_size", int(os.getenv("TOOL_CACHE_SIZE", "3"))),
    }


def _get_agent_for_room(room_name: str):
    result = session_registry.get(room_name)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No active session in room: {room_name}",
        )
    session, agent = result
    return session, agent


def _get_or_create_context(room_name: str) -> ChatContext:
    if room_name in _history_cache:
        return _history_cache[room_name]

    chat_ctx = ChatContext()
    prompt = settings_module.load_prompt_with_context(
        timezone_id=TIMEZONE_ID,
        timezone_display=TIMEZONE_DISPLAY,
    )
    chat_ctx.add_message(role="system", content=prompt)
    _history_cache[room_name] = chat_ctx
    return chat_ctx


def _trim_context(chat_ctx: ChatContext, max_turns: int) -> None:
    if max_turns <= 0:
        return

    items = chat_ctx.items
    if not items:
        return

    system_item = items[0] if getattr(items[0], "role", None) == "system" else None
    messages = [item for item in items if getattr(item, "role", None) != "system"]
    max_messages = max_turns * 2
    if len(messages) > max_messages:
        messages = messages[-max_messages:]

    chat_ctx.items = ([system_item] if system_item else []) + messages


def _build_greeting_instruction(settings: dict, instruction: str | None) -> str:
    if instruction:
        return instruction
    default = "Say a brief, friendly greeting. Do NOT use any tools - just greet."
    return settings.get("greeting_instruction", default)


async def _run_llm(agent, chat_ctx: ChatContext, runtime: dict, tool_cache: ToolDataCache) -> str:
    response_parts: list[str] = []
    async for chunk in ollama_llm_node(
        agent,
        chat_ctx,
        model=runtime["model"],
        think=OLLAMA_THINK,
        temperature=runtime["temperature"],
        num_ctx=runtime["num_ctx"],
        max_turns=runtime["max_turns"],
        tool_data_cache=tool_cache,
    ):
        response_parts.append(chunk)
    return "".join(response_parts).strip()


@app.post("/announce", response_model=AnnounceResponse)
async def announce(req: AnnounceRequest) -> AnnounceResponse:
    """Make the agent speak a message.

    This endpoint injects an announcement into an active voice session.
    The agent will speak the provided message using TTS.

    Args:
        req: AnnounceRequest with message and optional room_name

    Returns:
        AnnounceResponse with status

    Raises:
        HTTPException: 404 if no active session in the specified room
    """
    import session_registry

    result = session_registry.get(req.room_name)
    if not result:
        logger.warning(f"Announce failed: no session in room {req.room_name}")
        raise HTTPException(
            status_code=404,
            detail=f"No active session in room: {req.room_name}",
        )

    session, _agent = result
    logger.info(f"Announcing to room {req.room_name}: {req.message[:50]}...")

    # Say the message directly (bypasses LLM for instant response)
    await session.say(req.message)

    return AnnounceResponse(status="announced", room_name=req.room_name)


@app.post("/reload-tools", response_model=ReloadToolsResponse)
async def reload_tools(req: ReloadToolsRequest) -> ReloadToolsResponse:
    """Refresh MCP tool cache and optionally announce new tool availability.

    This endpoint clears the n8n workflow cache and re-discovers available
    workflows. Optionally announces the change:
    - If `message` is provided, speaks that exact message
    - If only `tool_name` is provided, speaks "A new tool called '{tool_name}' is now available."
    - If neither is provided, reloads silently

    Args:
        req: ReloadToolsRequest with optional message, tool_name, and room_name

    Returns:
        ReloadToolsResponse with status and tool count

    Raises:
        HTTPException: 404 if no active session in the specified room
    """
    import session_registry
    from integrations import n8n

    result = session_registry.get(req.room_name)
    if not result:
        logger.warning(f"Reload failed: no session in room {req.room_name}")
        raise HTTPException(
            status_code=404,
            detail=f"No active session in room: {req.room_name}",
        )

    session, agent = result
    logger.info(f"Reloading tools for room {req.room_name}")

    # Clear all caches
    agent._ollama_tools_cache = None
    n8n.clear_caches()

    # Re-discover n8n workflows if MCP is configured
    tool_count = 0
    if agent._n8n_mcp and agent._n8n_base_url:
        try:
            tools, name_map = await n8n.discover_n8n_workflows(
                agent._n8n_mcp, agent._n8n_base_url
            )
            agent._n8n_workflow_tools = tools
            agent._n8n_workflow_name_map = name_map
            tool_count = len(tools)
            logger.info(f"Discovered {tool_count} n8n workflows")
        except Exception as e:
            logger.error(f"Failed to re-discover n8n workflows: {e}")

    # Announce: custom message takes priority, then tool_name format
    if req.message:
        await session.say(req.message)
    elif req.tool_name:
        await session.say(f"A new tool called '{req.tool_name}' is now available.")

    return ReloadToolsResponse(
        status="reloaded",
        tool_count=tool_count,
        room_name=req.room_name,
    )


@app.post("/wake", response_model=WakeResponse)
async def wake(req: WakeRequest) -> WakeResponse:
    """Handle wake word detection - greet the user.

    This endpoint is called by the frontend when the wake word ("Hey Cal")
    is detected. The agent responds with a brief greeting to acknowledge
    the user and indicate readiness.

    Args:
        req: WakeRequest with room_name

    Returns:
        WakeResponse with status

    Raises:
        HTTPException: 404 if no active session in the specified room
    """
    import session_registry

    result = session_registry.get(req.room_name)
    if not result:
        logger.warning(f"Wake failed: no session in room {req.room_name}")
        raise HTTPException(
            status_code=404,
            detail=f"No active session in room: {req.room_name}",
        )

    session, _agent = result
    logger.info(f"Wake word detected in room {req.room_name}")

    # Say a random greeting directly (bypasses LLM for instant response)
    greetings = settings_module.get_setting("wake_greetings")
    greeting = random.choice(greetings)
    await session.say(greeting)

    return WakeResponse(status="greeted", room_name=req.room_name)


@app.post("/agent/greeting", response_model=GreetingResponse)
async def handle_agent_greeting(request: GreetingRequest) -> GreetingResponse:
    room_name = request.room_name or "voice_assistant_room"
    _session, agent = _get_agent_for_room(room_name)

    settings = settings_module.load_settings()
    instruction = _build_greeting_instruction(settings, request.instruction)
    runtime = _get_runtime_settings()

    chat_ctx = ChatContext()
    prompt = settings_module.load_prompt_with_context(
        timezone_id=TIMEZONE_ID,
        timezone_display=TIMEZONE_DISPLAY,
    )
    chat_ctx.add_message(role="system", content=prompt)
    chat_ctx.add_message(role="user", content=instruction)

    tool_cache = ToolDataCache(max_entries=runtime["tool_cache_size"])

    try:
        greeting_text = await _run_llm(agent, chat_ctx, runtime, tool_cache)
        if not greeting_text:
            raise ValueError("LLM returned empty greeting")
    except Exception as exc:
        logger.warning("LLM greeting failed, falling back to preset: %s", exc)
        greetings = settings.get("wake_greetings", ["Hello."])
        greeting_text = random.choice(greetings)

    # Get selected voice from settings
    tts_voice = settings.get("tts_voice", "ayhan")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            tts_response = await client.post(TTS_URL, json={"text": greeting_text, "voice": tts_voice})
            tts_response.raise_for_status()
            audio_url = tts_response.json().get("audio_url", "")
        except Exception as exc:
            logger.error("TTS for greeting failed: %s", exc)
            raise HTTPException(status_code=500, detail="TTS for greeting failed") from exc

    return GreetingResponse(text=greeting_text, audio_url=audio_url)


@app.post("/agent/query", response_model=AgentQueryResponse)
async def handle_agent_query(request: AgentQueryRequest) -> AgentQueryResponse:
    room_name = request.room_name or "voice_assistant_room"
    _session, agent = _get_agent_for_room(room_name)

    runtime = _get_runtime_settings()

    chat_ctx = _get_or_create_context(room_name)
    chat_ctx.add_message(role="user", content=request.transcript)

    tool_cache = _tool_data_cache_map.get(room_name)
    if not tool_cache:
        tool_cache = ToolDataCache(max_entries=runtime["tool_cache_size"])
        _tool_data_cache_map[room_name] = tool_cache

    try:
        response_text = await _run_llm(agent, chat_ctx, runtime, tool_cache)
    except Exception as exc:
        logger.error("LLM processing failed: %s", exc)
        response_text = (
            "I'm sorry, I encountered an error processing your request. "
            "Please try again."
        )

    if response_text:
        chat_ctx.add_message(role="assistant", content=response_text)
        _trim_context(chat_ctx, runtime["max_turns"])

    response_audio_url = ""
    if response_text:
        # Get selected voice from settings
        settings = settings_module.load_settings()
        tts_voice = settings.get("tts_voice", "ayhan")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                tts_response = await client.post(TTS_URL, json={"text": response_text, "voice": tts_voice})
                tts_response.raise_for_status()
                response_audio_url = tts_response.json().get("audio_url", "")
            except Exception as exc:
                logger.error("TTS failed: %s", exc)

    return AgentQueryResponse(
        response_text=response_text,
        response_audio_url=response_audio_url,
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint.

    Returns:
        HealthResponse with status and list of active session room names
    """
    import session_registry

    return HealthResponse(
        status="ok",
        active_sessions=session_registry.list_rooms(),
    )


@app.get("/status", response_model=AgentStatusResponse)
async def agent_status() -> AgentStatusResponse:
    """Expose aggregated STT/LLM/TTS readiness for the frontend."""
    return AgentStatusResponse(**get_status_snapshot())


# =============================================================================
# Settings Endpoints
# =============================================================================


class SettingsResponse(BaseModel):
    """Response body for /settings endpoint."""

    settings: dict
    prompt_content: str
    custom_prompt_exists: bool


class SettingsUpdateRequest(BaseModel):
    """Request body for POST /settings endpoint."""

    settings: dict


class PromptResponse(BaseModel):
    """Response body for /prompt endpoint."""

    prompt: str  # "default" or "custom"
    content: str
    is_custom: bool


class PromptUpdateRequest(BaseModel):
    """Request body for POST /prompt endpoint."""

    content: str


class VoicesResponse(BaseModel):
    """Response body for /voices endpoint."""

    voices: list[str]


class ModelsResponse(BaseModel):
    """Response body for /models endpoint."""

    models: list[str]


@app.get("/settings", response_model=SettingsResponse)
async def get_settings() -> SettingsResponse:
    """Get current settings and prompt content.

    Returns:
        SettingsResponse with current settings, prompt content, and custom prompt status
    """
    settings = settings_module.load_settings()
    prompt_content = settings_module.load_prompt_content()
    custom_exists = settings_module.custom_prompt_exists()

    return SettingsResponse(
        settings=settings,
        prompt_content=prompt_content,
        custom_prompt_exists=custom_exists,
    )


@app.post("/settings", response_model=SettingsResponse)
async def update_settings(req: SettingsUpdateRequest) -> SettingsResponse:
    """Update settings.

    Args:
        req: SettingsUpdateRequest with settings dict to merge

    Returns:
        SettingsResponse with updated settings
    """
    # Load current settings
    current = settings_module.load_settings()

    # Merge with new settings (only known keys)
    for key, value in req.settings.items():
        if key in settings_module.DEFAULT_SETTINGS:
            current[key] = value

    # Save merged settings
    settings_module.save_settings(current)

    # Reload and return
    settings = settings_module.reload_settings()
    prompt_content = settings_module.load_prompt_content()
    custom_exists = settings_module.custom_prompt_exists()

    logger.info(f"Settings updated: {list(req.settings.keys())}")

    return SettingsResponse(
        settings=settings,
        prompt_content=prompt_content,
        custom_prompt_exists=custom_exists,
    )


@app.get("/prompt", response_model=PromptResponse)
async def get_prompt() -> PromptResponse:
    """Get current prompt content.

    Returns:
        PromptResponse with prompt name and content
    """
    prompt_name = settings_module.get_setting("prompt", "default")
    content = settings_module.load_prompt_content(prompt_name)
    is_custom = prompt_name == "custom" and settings_module.custom_prompt_exists()

    return PromptResponse(
        prompt=prompt_name,
        content=content,
        is_custom=is_custom,
    )


@app.post("/prompt", response_model=PromptResponse)
async def save_prompt(req: PromptUpdateRequest) -> PromptResponse:
    """Save custom prompt content.

    Args:
        req: PromptUpdateRequest with content to save

    Returns:
        PromptResponse with saved prompt info
    """
    # Save to custom.md
    settings_module.save_custom_prompt(req.content)

    # Update settings to use custom prompt
    current = settings_module.load_settings()
    current["prompt"] = "custom"
    settings_module.save_settings(current)

    logger.info("Custom prompt saved and activated")

    return PromptResponse(
        prompt="custom",
        content=req.content,
        is_custom=True,
    )


@app.get("/voices", response_model=VoicesResponse)
async def get_voices() -> VoicesResponse:
    """Get available TTS voices from XTTS voices folder.

    Returns:
        VoicesResponse with list of voice IDs
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(TTS_VOICES_ENDPOINT, timeout=10.0)
            response.raise_for_status()
            payload = response.json()
            voices = payload.get("voices") or []
            if voices:
                return VoicesResponse(voices=sorted(voices))
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch voices from XTTS service: %s", exc)

    # Fallback to scanning local voice directory if service is unavailable
    voices_dir = os.getenv("XTTS_VOICES_DIR", "/app/voices")
    try:
        available = []
        if os.path.isdir(voices_dir):
            for filename in os.listdir(voices_dir):
                if filename.endswith(".wav"):
                    available.append(filename[:-4])
        if available:
            return VoicesResponse(voices=sorted(available))
        logger.warning("No voices found in %s", voices_dir)
    except Exception as exc:
        logger.warning("Failed to scan voices directory %s: %s", voices_dir, exc)

    return VoicesResponse(voices=["ayhan", "serdar"])


@app.get("/models", response_model=ModelsResponse)
async def get_models() -> ModelsResponse:
    """Get available LLM models from Ollama.

    Returns:
        ModelsResponse with list of model names
    """
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ollama_host}/api/tags",
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            # Ollama returns {"models": [{"name": "...", ...}, ...]}
            models = [m.get("name") for m in data.get("models", [])]
            models = [m for m in models if m]  # Filter None values

            return ModelsResponse(models=models)
    except Exception as e:
        logger.warning(f"Failed to fetch models from Ollama: {e}")
        # Return empty list on failure
        return ModelsResponse(models=[])
