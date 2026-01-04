from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from livekit import rtc
from livekit.agents import (
    APIConnectOptions,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    stt,
    tts,
    vad,
)
from livekit.agents.stt import (
    RecognitionUsage,
    SpeechData,
    SpeechEvent,
    SpeechEventType,
    STTCapabilities,
)
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, NotGivenOr, NOT_GIVEN
from livekit.agents.utils import AudioBuffer, combine_frames, is_given
from livekit.agents.utils.audio import calculate_audio_duration

SPEECH_STT_ENDPOINT = "/v1/audio/transcriptions"
SPEECH_TTS_ENDPOINT = "/v1/audio/speech"
DEFAULT_TTS_FORMAT = "mp3"
DEFAULT_TTS_VOICE = "jenny_dioco"
DEFAULT_TTS_MODEL = "speaches-ai/piper-en_GB-jenny_dioco-medium"
DEFAULT_STT_MODEL = "Systran/faster-whisper-medium"
DEFAULT_TTS_SPEED = 1.0
DEFAULT_SPEECH_TIMEOUT = 30.0
DEFAULT_VAD_THRESHOLD = 500
DEFAULT_VAD_MIN_SPEECH = 0.1
DEFAULT_VAD_SILENCE = 0.35

logger = logging.getLogger("SpeechClient")


def _build_headers(api_key: str | None, accept: str) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": accept}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _extract_transcription(body: Any) -> str | None:
    if isinstance(body, str):
        text = body.strip()
        return text or None

    if isinstance(body, list):
        for part in body:
            candidate = _extract_transcription(part)
            if candidate:
                return candidate
        return None

    if isinstance(body, dict):
        for key in ("text", "transcript", "transcription", "result", "output"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        for key in ("segments", "alternatives", "data"):
            value = body.get(key)
            if isinstance(value, list):
                for item in value:
                    candidate = _extract_transcription(item)
                    if candidate:
                        return candidate

    return None


def _extract_language(body: Any) -> str | None:
    if isinstance(body, dict):
        for key in ("language", "lang", "detected_language"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for key in ("segments", "alternatives", "data"):
            value = body.get(key)
            if isinstance(value, list):
                for item in value:
                    candidate = _extract_language(item)
                    if candidate:
                        return candidate
    return None


@dataclass
class DrascomSttOptions:
    base_url: str
    model: str = DEFAULT_STT_MODEL
    language: str | None = None
    response_format: str = "json"
    api_key: str | None = None
    timeout: float = DEFAULT_SPEECH_TIMEOUT


class DrascomSTT(stt.STT):
    def __init__(
        self,
        *,
        base_url: str,
        model: str = DEFAULT_STT_MODEL,
        language: str | None = None,
        response_format: str = "json",
        api_key: str | None = None,
        timeout: float = DEFAULT_SPEECH_TIMEOUT,
    ) -> None:
        super().__init__(capabilities=STTCapabilities(streaming=False, interim_results=False))
        self._opts = DrascomSttOptions(
            base_url=base_url.rstrip("/"),
            model=model,
            language=language,
            response_format=response_format,
            api_key=api_key,
            timeout=timeout,
        )
        self._client = httpx.AsyncClient(
            headers=_build_headers(api_key, "application/json"),
            timeout=httpx.Timeout(timeout),
        )

    @staticmethod
    def _ensure_buffer_frame(buffer: AudioBuffer) -> rtc.AudioFrame:
        if isinstance(buffer, list):
            return combine_frames(buffer)
        return buffer

    @staticmethod
    def _serialize_audio(buffer: AudioBuffer) -> bytes:
        frame = DrascomSTT._ensure_buffer_frame(buffer)
        return frame.to_wav_bytes()

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> SpeechEvent:
        wav_bytes = self._serialize_audio(buffer)
        audio_duration = calculate_audio_duration(buffer)

        payload: dict[str, Any] = {
            "model": self._opts.model,
            "response_format": self._opts.response_format,
        }
        if self._opts.language:
            payload["language"] = self._opts.language
        elif is_given(language):
            payload["language"] = language

        url = f"{self._opts.base_url}{SPEECH_STT_ENDPOINT}"

        try:
            response = await self._client.post(
                url,
                data=payload,
                files={"file": ("input.wav", wav_bytes, "audio/wav")},
                timeout=httpx.Timeout(conn_options.timeout),
            )
            response.raise_for_status()
            try:
                body = response.json()
            except ValueError:
                body = response.text
        except httpx.HTTPStatusError as exc:
            raise APIStatusError(
                f"stt request failed ({exc.response.status_code})",
                status_code=exc.response.status_code,
                request_id=exc.response.headers.get("x-request-id"),
                body=exc.response.text,
            ) from exc
        except httpx.TimeoutException as exc:
            raise APITimeoutError() from exc
        except (httpx.RequestError, OSError) as exc:  # pragma: no cover - defensive
            raise APIConnectionError() from exc

        transcript = _extract_transcription(body)
        detected_language = _extract_language(body)
        language_code = (
            detected_language
            or self._opts.language
            or (language if is_given(language) else None)
            or ""
        )

        if not transcript:
            logger.debug(
                "stt empty transcript (duration=%.2fs, language=%s)",
                audio_duration,
                language_code or "unknown",
            )
            return SpeechEvent(
                type=SpeechEventType.FINAL_TRANSCRIPT,
                request_id=response.headers.get("x-request-id", ""),
                alternatives=[],
                recognition_usage=RecognitionUsage(audio_duration=audio_duration),
            )

        logger.info(
            "stt transcript (duration=%.2fs, language=%s): %s",
            audio_duration,
            language_code or "unknown",
            transcript,
        )
        return SpeechEvent(
            type=SpeechEventType.FINAL_TRANSCRIPT,
            request_id=response.headers.get("x-request-id", ""),
            alternatives=[SpeechData(text=transcript, language=language_code)],
            recognition_usage=RecognitionUsage(audio_duration=audio_duration),
        )

    async def aclose(self) -> None:
        await self._client.aclose()


@dataclass
class DrascomTtsOptions:
    base_url: str
    model: str = DEFAULT_TTS_MODEL
    voice: str = DEFAULT_TTS_VOICE
    speed: float = DEFAULT_TTS_SPEED
    response_format: str = DEFAULT_TTS_FORMAT
    api_key: str | None = None
    timeout: float = DEFAULT_SPEECH_TIMEOUT


class DrascomTTS(tts.TTS):
    def __init__(
        self,
        *,
        base_url: str,
        model: str = DEFAULT_TTS_MODEL,
        voice: str = DEFAULT_TTS_VOICE,
        speed: float = DEFAULT_TTS_SPEED,
        response_format: str = DEFAULT_TTS_FORMAT,
        api_key: str | None = None,
        timeout: float = DEFAULT_SPEECH_TIMEOUT,
    ) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=24000,
            num_channels=1,
        )
        self._opts = DrascomTtsOptions(
            base_url=base_url.rstrip("/"),
            model=model,
            voice=voice,
            speed=speed,
            response_format=response_format,
            api_key=api_key,
            timeout=timeout,
        )
        self._client = httpx.AsyncClient(
            headers=_build_headers(api_key, "audio/mpeg"),
            timeout=httpx.Timeout(timeout),
        )

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> tts.ChunkedStream:
        return _DrascomTTSSynthesizedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
        )

    def update_options(
        self,
        *,
        model: str | None = None,
        voice: str | None = None,
        speed: float | None = None,
        response_format: str | None = None,
    ) -> None:
        if model:
            self._opts.model = model
        if voice:
            self._opts.voice = voice
        if speed is not None:
            self._opts.speed = speed
        if response_format:
            self._opts.response_format = response_format

    async def aclose(self) -> None:
        await self._client.aclose()


class _DrascomTTSSynthesizedStream(tts.ChunkedStream):
    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        url = f"{self._tts._opts.base_url}{SPEECH_TTS_ENDPOINT}"
        payload = {
            "model": self._tts._opts.model,
            "voice": self._tts._opts.voice,
            "input": self.input_text,
            "response_format": self._tts._opts.response_format,
            "speed": self._tts._opts.speed,
        }
        logger.info(
            "tts request (model=%s, voice=%s, format=%s, speed=%.2f): %s",
            self._tts._opts.model,
            self._tts._opts.voice,
            self._tts._opts.response_format,
            self._tts._opts.speed,
            self.input_text,
        )

        try:
            response = await self._tts._client.post(
                url,
                json=payload,
                timeout=httpx.Timeout(self._conn_options.timeout),
            )
            response.raise_for_status()
            mime_type = response.headers.get("content-type", "audio/mpeg")
        except httpx.HTTPStatusError as exc:
            raise APIStatusError(
                f"tts request failed ({exc.response.status_code})",
                status_code=exc.response.status_code,
                request_id=exc.response.headers.get("x-request-id"),
                body=exc.response.text,
            ) from exc
        except httpx.TimeoutException as exc:
            raise APITimeoutError() from exc
        except (httpx.RequestError, OSError) as exc:  # pragma: no cover - defensive
            raise APIConnectionError() from exc

        request_id = response.headers.get("x-request-id", "")
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=self._tts.sample_rate,
            num_channels=self._tts.num_channels,
            mime_type=mime_type,
        )
        output_emitter.push(response.content)
        output_emitter.flush()


class SimpleEnergyVAD(vad.VAD):
    def __init__(
        self,
        *,
        threshold: int = DEFAULT_VAD_THRESHOLD,
        min_speech_duration: float = DEFAULT_VAD_MIN_SPEECH,
        silence_timeout: float = DEFAULT_VAD_SILENCE,
    ) -> None:
        super().__init__(capabilities=vad.VADCapabilities(update_interval=0.1))
        self._threshold = threshold
        self._min_speech_duration = min_speech_duration
        self._silence_timeout = silence_timeout

    def stream(self) -> vad.VADStream:
        return _SimpleEnergyVADStream(
            vad=self,
            threshold=self._threshold,
            min_speech_duration=self._min_speech_duration,
            silence_timeout=self._silence_timeout,
        )


class _SimpleEnergyVADStream(vad.VADStream):
    def __init__(
        self,
        *,
        vad: vad.VAD,
        threshold: int,
        min_speech_duration: float,
        silence_timeout: float,
    ) -> None:
        super().__init__(vad=vad)
        self._threshold = threshold
        self._min_speech_duration = min_speech_duration
        self._silence_timeout = silence_timeout
        self._speech_frames: list[rtc.AudioFrame] = []
        self._pending_frames: list[rtc.AudioFrame] = []
        self._pending_duration = 0.0
        self._speech_duration = 0.0
        self._silence_accumulated = 0.0
        self._speech_started = False
        self._speech_start_index = 0
        self._samples_index = 0

    async def _main_task(self) -> None:
        try:
            async for chunk in self._input_ch:
                if isinstance(chunk, self._FlushSentinel):
                    if self._speech_started:
                        self._emit_end()
                    continue
                self._process_frame(chunk)
        finally:
            if self._speech_started:
                self._emit_end()

    def _process_frame(self, frame: rtc.AudioFrame) -> None:
        amplitude = self._frame_amplitude(frame)
        duration = frame.duration or (frame.samples_per_channel / frame.sample_rate if frame.sample_rate else 0.0)
        silence_exceeded = False

        if amplitude >= self._threshold:
            self._silence_accumulated = 0.0
            if self._speech_started:
                self._speech_frames.append(frame)
                self._speech_duration += duration
            else:
                self._pending_frames.append(frame)
                self._pending_duration += duration
                if self._pending_duration >= self._min_speech_duration:
                    self._start_speech()
        else:
            if self._speech_started:
                self._silence_accumulated += duration
                if self._silence_accumulated >= self._silence_timeout:
                    silence_exceeded = True

        self._samples_index += frame.samples_per_channel

        if silence_exceeded:
            self._emit_end()

    def _start_speech(self) -> None:
        self._speech_started = True
        self._speech_start_index = self._samples_index
        self._speech_frames = list(self._pending_frames)
        self._speech_duration = self._pending_duration
        self._pending_frames.clear()
        self._pending_duration = 0.0

        self._event_ch.send_nowait(
            vad.VADEvent(
                type=vad.VADEventType.START_OF_SPEECH,
                samples_index=self._speech_start_index,
                timestamp=time.time(),
                speech_duration=0.0,
                silence_duration=0.0,
                frames=list(self._speech_frames),
            )
        )

    def _emit_end(self) -> None:
        if not self._speech_started:
            return

        self._event_ch.send_nowait(
            vad.VADEvent(
                type=vad.VADEventType.END_OF_SPEECH,
                samples_index=self._speech_start_index,
                timestamp=time.time(),
                speech_duration=self._speech_duration,
                silence_duration=self._silence_accumulated,
                frames=list(self._speech_frames),
            )
        )
        self._speech_started = False
        self._speech_frames.clear()
        self._speech_duration = 0.0
        self._silence_accumulated = 0.0
        self._pending_frames.clear()
        self._pending_duration = 0.0

    @staticmethod
    def _frame_amplitude(frame: rtc.AudioFrame) -> int:
        raw = frame.data.tobytes() if isinstance(frame.data, memoryview) else frame.data
        if not raw or len(raw) < 2:
            return 0
        if len(raw) % 2 != 0:
            raw = raw[: len(raw) - 1]
        view = memoryview(raw).cast("h")
        if not view:
            return 0
        return max(abs(sample) for sample in view)
