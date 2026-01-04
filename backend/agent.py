from dotenv import load_dotenv
from prompts import get_system_prompt, get_session_instruction, get_random_greeting
from livekit import agents
from livekit.agents import AgentSession, Agent
try:
    from livekit.agents import RoomOptions
except ImportError:
    RoomOptions = None  # type: ignore
    from livekit.agents import RoomInputOptions
from livekit.plugins import openai
# Note: noise_cancellation requires LiveKit Cloud, not used for self-hosted
import os
import logging
import threading
import uvicorn
from tools import open_url
from session import registry
from settings import settings_manager
from speech_client import (
    DEFAULT_SPEECH_TIMEOUT,
    DEFAULT_STT_MODEL,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_VOICE,
    DEFAULT_TTS_SPEED,
    DEFAULT_VAD_MIN_SPEECH,
    DEFAULT_VAD_SILENCE,
    DEFAULT_VAD_THRESHOLD,
    DrascomSTT,
    DrascomTTS,
    SimpleEnergyVAD,
)
load_dotenv()


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _ensure_ollama_base(url: str) -> str:
    cleaned = url.rstrip("/")
    if cleaned.endswith("/v1"):
        return cleaned
    return f"{cleaned}/v1"


OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama.drscom.uk")
OLLAMA_BASE_URL = _ensure_ollama_base(OLLAMA_BASE_URL)
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL")

SPEECH_SERVER_URL = os.environ.get("SPEECH_SERVER_URL", "https://speech.drascom.uk").rstrip("/")
SPEECH_SERVER_API_KEY = os.environ.get("SPEECH_SERVER_API_KEY")
SPEECH_SERVER_TTS_MODEL = os.environ.get("SPEECH_SERVER_TTS_MODEL", DEFAULT_TTS_MODEL)
SPEECH_SERVER_TTS_VOICE = os.environ.get("SPEECH_SERVER_TTS_VOICE", DEFAULT_TTS_VOICE)
SPEECH_SERVER_TTS_RESPONSE_FORMAT = os.environ.get("SPEECH_SERVER_TTS_RESPONSE_FORMAT", "mp3")
SPEECH_SERVER_TTS_SPEED = _env_float("SPEECH_SERVER_TTS_SPEED", DEFAULT_TTS_SPEED)
SPEECH_SERVER_TTS_TIMEOUT = _env_float("SPEECH_SERVER_TTS_TIMEOUT", DEFAULT_SPEECH_TIMEOUT)
SPEECH_SERVER_TTS_MODEL_TR = os.environ.get(
    "SPEECH_SERVER_TTS_MODEL_TR", "speaches-ai/piper-tr_TR-fahrettin-medium"
)
SPEECH_SERVER_TTS_VOICE_TR = os.environ.get("SPEECH_SERVER_TTS_VOICE_TR", "fahrettin")

SPEECH_SERVER_STT_MODEL = os.environ.get("SPEECH_SERVER_STT_MODEL", DEFAULT_STT_MODEL)
SPEECH_SERVER_STT_RESPONSE_FORMAT = os.environ.get(
    "SPEECH_SERVER_STT_RESPONSE_FORMAT", "verbose_json"
)
SPEECH_SERVER_LANGUAGE = os.environ.get("SPEECH_SERVER_LANGUAGE")
SPEECH_SERVER_STT_TIMEOUT = _env_float("SPEECH_SERVER_STT_TIMEOUT", DEFAULT_SPEECH_TIMEOUT)

SPEECH_VAD_THRESHOLD = _env_int("SPEECH_VAD_THRESHOLD", DEFAULT_VAD_THRESHOLD)
SPEECH_VAD_MIN_SPEECH_DURATION = _env_float(
    "SPEECH_VAD_MIN_SPEECH_DURATION", DEFAULT_VAD_MIN_SPEECH
)
SPEECH_VAD_SILENCE_TIMEOUT = _env_float(
    "SPEECH_VAD_SILENCE_TIMEOUT", DEFAULT_VAD_SILENCE
)
ENABLE_MCP = _env_bool("ENABLE_MCP", False)


class Assistant(Agent):
    def __init__(self, user_name: str | None = None) -> None:
        system_prompt = get_system_prompt(user_name=user_name)
        self._base_instructions = system_prompt
        self._user_name = user_name
        self._last_language: str | None = None
        self._active_language: str | None = None
        super().__init__(instructions=self._base_instructions, tools=[open_url])

    @staticmethod
    def _normalize_language(language: str) -> str:
        return language.strip().lower().replace("_", "-")

    def _coerce_language(self, language: str | None) -> str | None:
        if not language:
            return None
        normalized = self._normalize_language(language)
        if self._is_turkish(normalized):
            return "tr"
        if normalized in ("en", "en-us", "en-gb", "english"):
            return "en"
        return "en"

    def set_detected_language(self, language: str | None) -> None:
        coerced = self._coerce_language(language)
        if not coerced:
            return
        self._last_language = coerced

    def _is_turkish(self, language: str | None) -> bool:
        if not language:
            return False
        language = self._normalize_language(language)
        return language in ("tr", "tr-tr", "turkish")

    def _language_instructions(self, language: str | None) -> str:
        if self._is_turkish(language):
            return "Respond in Turkish."
        return "Respond in English."

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        await super().on_user_turn_completed(turn_ctx, new_message)
        if not self._last_language:
            return
        if self._last_language == self._active_language:
            return
        self._active_language = self._last_language
        instructions = f"{self._base_instructions}\n{self._language_instructions(self._active_language)}"
        await self.update_instructions(instructions)

        try:
            activity = self._get_activity_or_raise()
        except RuntimeError:
            return

        tts_engine = activity.tts
        if not isinstance(tts_engine, DrascomTTS):
            return

        if self._is_turkish(self._active_language):
            tts_engine.update_options(
                model=SPEECH_SERVER_TTS_MODEL_TR,
                voice=SPEECH_SERVER_TTS_VOICE_TR,
                response_format=SPEECH_SERVER_TTS_RESPONSE_FORMAT,
                speed=SPEECH_SERVER_TTS_SPEED,
            )
        else:
            tts_engine.update_options(
                model=SPEECH_SERVER_TTS_MODEL,
                voice=SPEECH_SERVER_TTS_VOICE,
                response_format=SPEECH_SERVER_TTS_RESPONSE_FORMAT,
                speed=SPEECH_SERVER_TTS_SPEED,
            )


logger = logging.getLogger("Brain")
logging.getLogger("livekit.agents").setLevel(logging.DEBUG)
logging.getLogger("livekit").setLevel(logging.DEBUG)


async def entrypoint(ctx: agents.JobContext):
    # Connect first to get participant info
    await ctx.connect()

    # Get participant info
    room_name = ctx.room.name
    user_identity = "unknown"
    user_name = "User"

    for participant in ctx.room.remote_participants.values():
        user_identity = participant.identity
        user_name = participant.name or participant.identity
        break

    logger.info(f"User '{user_name}' joined room '{room_name}'")

    # Setup LLM
    model_kwargs = {
        "base_url": OLLAMA_BASE_URL,
    }
    settings_model = settings_manager.settings.llm_model
    if OLLAMA_MODEL:
        model_kwargs["model"] = OLLAMA_MODEL
    elif settings_model:
        model_kwargs["model"] = settings_model
    logger.debug("LLM init params: %s", model_kwargs)

    # Setup speech services
    speech_stt = DrascomSTT(
        base_url=SPEECH_SERVER_URL,
        api_key=SPEECH_SERVER_API_KEY,
        model=SPEECH_SERVER_STT_MODEL,
        language=SPEECH_SERVER_LANGUAGE,
        response_format=SPEECH_SERVER_STT_RESPONSE_FORMAT,
        timeout=SPEECH_SERVER_STT_TIMEOUT,
    )
    speech_tts = DrascomTTS(
        base_url=SPEECH_SERVER_URL,
        api_key=SPEECH_SERVER_API_KEY,
        model=SPEECH_SERVER_TTS_MODEL,
        voice=SPEECH_SERVER_TTS_VOICE,
        speed=SPEECH_SERVER_TTS_SPEED,
        response_format=SPEECH_SERVER_TTS_RESPONSE_FORMAT,
        timeout=SPEECH_SERVER_TTS_TIMEOUT,
    )
    speech_vad = SimpleEnergyVAD(
        threshold=SPEECH_VAD_THRESHOLD,
        min_speech_duration=SPEECH_VAD_MIN_SPEECH_DURATION,
        silence_timeout=SPEECH_VAD_SILENCE_TIMEOUT,
    )

    # Create session
    session = AgentSession(
        llm=openai.LLM.with_ollama(**model_kwargs),
        stt=speech_stt,
        tts=speech_tts,
        vad=speech_vad,
    )

    # Create agent with user's name for personalized prompts
    if ENABLE_MCP:
        from mcp_client import MCPServerSse
        from mcp_client.agent_tools import MCPToolsIntegration

        mcp_server = MCPServerSse(
            params={"url": os.environ.get("N8N_MCP_SERVER_URL")},
            cache_tools_list=True,
            name="SSE MCP Server"
        )

        agent = await MCPToolsIntegration.create_agent_with_tools(
            agent_class=Assistant,
            mcp_servers=[mcp_server],
            agent_kwargs={"user_name": user_name}
        )
    else:
        agent = Assistant(user_name=user_name)

    def _on_user_transcribed(ev):
        if ev.is_final:
            agent.set_detected_language(ev.language)

    session.on("user_input_transcribed", _on_user_transcribed)

    # Start session
    start_kwargs = {
        "room": ctx.room,
        "agent": agent,
        # Note: noise_cancellation.BVC() requires LiveKit Cloud
        # For self-hosted, omit the noise_cancellation parameter
    }
    if RoomOptions is not None:
        start_kwargs["room_options"] = RoomOptions()
    else:
        start_kwargs["room_input_options"] = RoomInputOptions()

    await session.start(**start_kwargs)

    # Register session
    await registry.register(
        room_name=room_name,
        user_identity=user_identity,
        user_name=user_name,
        agent_session=session,
        agent=agent,
    )
    logger.info(f"Session registered for room '{room_name}'")

    # Cleanup on disconnect (must be sync, use create_task for async work)
    def on_disconnect():
        import asyncio
        asyncio.create_task(registry.unregister(room_name))
        logger.info(f"Session unregistered for room '{room_name}'")

    ctx.room.on("disconnected", on_disconnect)

    # Generate initial greeting if enough time has passed
    if registry.should_greet(user_identity):
        greeting_instruction = get_session_instruction()
        await session.generate_reply(
            instructions=greeting_instruction,
        )
        registry.record_greeting(user_identity)


def start_api_server(port: int = 8889):
    """Start the FastAPI server in a background thread."""
    from api import app

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    logger.info(f"API server started on port {port}")
    return thread


if __name__ == "__main__":
    # Start API server in background
    api_port = int(os.environ.get("API_PORT", 8889))
    start_api_server(api_port)

    # Start LiveKit agent
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
