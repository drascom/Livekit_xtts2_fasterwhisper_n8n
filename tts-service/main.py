import asyncio
import logging
import os
import re
import uuid
from pathlib import Path

import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from TTS.api import TTS

logger = logging.getLogger("tts-service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI()

MODEL_NAME = os.getenv("XTTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
VOICE_DIR = Path(os.getenv("XTTS_VOICES_DIR", "/app/voices"))
DEFAULT_VOICE = os.getenv("XTTS_DEFAULT_VOICE", "default")
DEFAULT_LANGUAGE = os.getenv("XTTS_DEFAULT_LANGUAGE", "en")
MEDIA_DIR = Path(os.getenv("TTS_MEDIA_DIR", "/tmp/tts-media"))
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

VOICE_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")
TURKISH_WORDS_RE = re.compile(
    r"\b(ve|bir|ben|sen|biz|siz|neden|nasil|degil|evet|hayir|merhaba|tesekkur|lutfen)\b",
    re.IGNORECASE,
)

SPEAKER_IDS: set[str] = set()
tts_model: TTS | None = None
tts_model_ready = False


def _detect_language(text: str) -> str:
    if any(ch in TURKISH_CHARS for ch in text):
        return "tr"
    if TURKISH_WORDS_RE.search(text):
        return "tr"
    return "en"


def _select_voice(voice_name: str | None) -> tuple[str, Path | None, str | None]:
    candidate_voice = (voice_name or DEFAULT_VOICE).strip()
    if not candidate_voice:
        candidate_voice = DEFAULT_VOICE

    speaker_path = resolve_speaker_wav(candidate_voice)
    if speaker_path:
        return candidate_voice, speaker_path, None

    if candidate_voice != DEFAULT_VOICE:
        fallback_path = resolve_speaker_wav(DEFAULT_VOICE)
        if fallback_path:
            logger.warning(
                "Voice %s not found, falling back to default voice %s",
                candidate_voice,
                DEFAULT_VOICE,
            )
            return DEFAULT_VOICE, fallback_path, None

    if candidate_voice in SPEAKER_IDS:
        return candidate_voice, None, candidate_voice

    if DEFAULT_VOICE in SPEAKER_IDS:
        return DEFAULT_VOICE, None, DEFAULT_VOICE

    raise HTTPException(
        status_code=400,
        detail="No valid speaker available; add a WAV into XTTS_VOICES_DIR or configure XTTS_DEFAULT_VOICE",
    )


def resolve_speaker_wav(voice_name: str | None) -> Path | None:
    if not voice_name:
        voice_name = DEFAULT_VOICE
    candidate = VOICE_DIR / f"{voice_name}.wav"
    if candidate.is_file():
        return candidate
    return None


def _refresh_speaker_ids(tts: TTS) -> None:
    global SPEAKER_IDS
    tts_model_obj = getattr(tts, "tts_model", None)
    speaker_manager = getattr(tts_model_obj, "speaker_manager", None)
    if speaker_manager and hasattr(speaker_manager, "speakers"):
        SPEAKER_IDS = set(speaker_manager.speakers.keys())


def get_tts_model() -> TTS:
    global tts_model
    if tts_model is None:
        logger.info("Loading XTTS model %s (device=%s)", MODEL_NAME, DEVICE)
        loaded = TTS(MODEL_NAME, progress_bar=False).to(DEVICE)
        _refresh_speaker_ids(loaded)
        tts_model = loaded
    return tts_model


@app.on_event("startup")
async def preload_tts_model() -> None:
    """Warm up the XTTS model on startup so the first request is fast."""
    global tts_model_ready

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    try:
        if loop:
            await loop.run_in_executor(None, get_tts_model)
        else:
            get_tts_model()
        tts_model_ready = True
        logger.info("XTTS model preloaded")
    except Exception as exc:
        logger.exception("Failed to preload XTTS model: %s", exc)
        tts_model_ready = False


@app.get("/health")
async def health() -> dict[str, object]:
    """Health endpoint used by the voice agent to inspect XTTS readiness."""

    return {
        "status": "ok",
        "model_ready": tts_model_ready,
    }


def _normalize_language(requested_language: str | None, text: str) -> str:
    language = (requested_language or "auto").lower()
    if language in ("", "auto"):
        language = _detect_language(text)
        logger.info("Auto-detected language %s for text", language)
    elif language == "default":
        language = DEFAULT_LANGUAGE
    return language


def _synthesize_to_file(text: str, voice_name: str | None, language: str, speed: float) -> Path:
    voice, speaker_wav, speaker_id = _select_voice(voice_name)
    tts = get_tts_model()
    filename = f"{uuid.uuid4().hex}.wav"
    file_path = MEDIA_DIR / filename

    tts_kwargs = {
        "text": text,
        "language": language,
        "speed": speed,
        "file_path": str(file_path),
    }
    if speaker_wav:
        tts_kwargs["speaker_wav"] = str(speaker_wav)
    elif speaker_id:
        tts_kwargs["speaker"] = speaker_id

    tts.tts_to_file(**tts_kwargs)
    return file_path


class TTSRequest(BaseModel):
    text: str = Field(..., description="Plain text to synthesize")
    voice: str | None = Field(None, description="Optional voice name (filename without .wav)")
    language: str | None = Field(None, description="Language hint (auto|tr|en|default)")
    speed: float | None = Field(1.0, description="Speed multiplier")


class SpeechRequest(BaseModel):
    input: str = Field(..., description="Text to synthesize (OpenAI compatible)")
    model: str | None = Field(None, description="Ignored for compatibility")
    voice: str | None = Field(None, description="Voice/speaker override. Can include language suffix like 'voice:tr' or 'voice:en'")
    language: str | None = Field(None, description="Language hint (auto|tr|en|default)")
    speed: float | None = Field(1.0, description="Speed multiplier")


def _parse_voice_and_language(voice: str | None, language: str | None) -> tuple[str | None, str | None]:
    """Parse voice name and extract language if encoded as 'voice:lang'.

    Supports formats:
    - "ayhan" -> voice="ayhan", language=None (use passed language param)
    - "ayhan:tr" -> voice="ayhan", language="tr"
    - "ayhan:en" -> voice="ayhan", language="en"
    - "ayhan:auto" -> voice="ayhan", language="auto"

    Returns:
        Tuple of (voice_name, language)
    """
    if not voice:
        return voice, language

    if ":" in voice:
        parts = voice.split(":", 1)
        parsed_voice = parts[0]
        parsed_lang = parts[1] if len(parts) > 1 else None
        # Voice-encoded language overrides the language parameter
        if parsed_lang and parsed_lang in ("auto", "en", "tr"):
            return parsed_voice, parsed_lang
        return parsed_voice, language

    return voice, language


class TTSResponse(BaseModel):
    audio_url: str


@app.post("/tts/synthesize")
async def synthesize_speech(request: TTSRequest) -> TTSResponse:
    text = (request.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    language = _normalize_language(request.language, text)
    speed = max(0.1, request.speed or 1.0)

    try:
        file_path = _synthesize_to_file(text, request.voice, language, speed)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("TTS failed")
        raise HTTPException(status_code=500, detail=f"TTS failed: {exc}") from exc

    audio_url = f"http://tts-service:8003/media/{file_path.name}"
    return TTSResponse(audio_url=audio_url)


@app.post("/v1/audio/speech")
async def synthesize_openai_tts(request: SpeechRequest) -> Response:
    text = (request.input or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Input text is required")

    # Parse voice name for embedded language (e.g., "ayhan:tr")
    voice, lang_from_voice = _parse_voice_and_language(request.voice, request.language)
    language = _normalize_language(lang_from_voice, text)
    speed = max(0.1, request.speed or 1.0)

    try:
        file_path = _synthesize_to_file(text, voice, language, speed)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("OVFT (OpenAI compat) TTS failed")
        raise HTTPException(status_code=500, detail=f"TTS failed: {exc}") from exc

    try:
        with open(file_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
    finally:
        file_path.unlink(missing_ok=True)

    return Response(content=audio_bytes, media_type="audio/wav")


@app.get("/v1/audio/voices")
async def list_voices():
    try:
        voices = sorted(p.stem for p in VOICE_DIR.glob("*.wav"))
        return {"voices": voices}
    except Exception as exc:
        logger.exception("Failed to list voices")
        raise HTTPException(status_code=500, detail=f"Failed to list voices: {exc}") from exc


@app.get("/media/{filename}")
async def get_audio_file(filename: str):
    file_path = MEDIA_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    media_type = "audio/wav" if filename.endswith(".wav") else "audio/mpeg"
    return FileResponse(path=file_path, media_type=media_type)
