"""
Shared fixtures for STT and TTS service tests.

These tests run against live Docker containers.
Ensure services are running: docker compose up -d stt-service tts-service
"""
import os
import pytest
import httpx

# Service URLs - configurable via environment variables
STT_SERVICE_URL = os.getenv("STT_SERVICE_URL", "http://localhost:8000")
TTS_SERVICE_URL = os.getenv("TTS_SERVICE_URL", "http://localhost:8003")

# Timeouts for different operations
HEALTH_CHECK_TIMEOUT = 5.0
TRANSCRIPTION_TIMEOUT = 30.0
TTS_TIMEOUT = 60.0  # TTS can be slow, especially on first load


@pytest.fixture(scope="session")
def stt_base_url() -> str:
    """Base URL for STT service (Speaches)."""
    return STT_SERVICE_URL


@pytest.fixture(scope="session")
def tts_base_url() -> str:
    """Base URL for TTS service (XTTS)."""
    return TTS_SERVICE_URL


@pytest.fixture(scope="session")
def http_client():
    """Synchronous HTTP client for tests."""
    with httpx.Client(timeout=60.0) as client:
        yield client


@pytest.fixture(scope="session")
async def async_http_client():
    """Async HTTP client for async tests."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client


@pytest.fixture(scope="session")
def sample_audio_path(tmp_path_factory) -> str:
    """
    Generate a simple WAV audio file for testing.
    Creates a 1-second silent audio file.
    """
    import wave
    import struct

    tmp_dir = tmp_path_factory.mktemp("audio")
    audio_path = tmp_dir / "test_audio.wav"

    # Audio parameters
    sample_rate = 16000
    duration = 1  # seconds
    num_samples = sample_rate * duration

    # Create silent audio (zeros)
    samples = [0] * num_samples

    with wave.open(str(audio_path), 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)

        for sample in samples:
            wav_file.writeframes(struct.pack('<h', sample))

    return str(audio_path)


@pytest.fixture(scope="session")
def sample_speech_audio_path(tmp_path_factory) -> str:
    """
    Generate a WAV file with simple tone for testing.
    Creates a 1-second audio file with a 440Hz sine wave.
    """
    import wave
    import struct
    import math

    tmp_dir = tmp_path_factory.mktemp("speech_audio")
    audio_path = tmp_dir / "test_speech.wav"

    # Audio parameters
    sample_rate = 16000
    duration = 1  # seconds
    frequency = 440  # Hz (A4 note)
    amplitude = 16000

    num_samples = sample_rate * duration

    # Generate sine wave
    samples = []
    for i in range(num_samples):
        sample = int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
        samples.append(sample)

    with wave.open(str(audio_path), 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)

        for sample in samples:
            wav_file.writeframes(struct.pack('<h', sample))

    return str(audio_path)


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "stt: marks tests for STT service (Speaches)"
    )
    config.addinivalue_line(
        "markers", "tts: marks tests for TTS service (XTTS)"
    )
    config.addinivalue_line(
        "markers", "integration: marks integration tests requiring running containers"
    )
    config.addinivalue_line(
        "markers", "slow: marks slow tests (TTS generation, etc.)"
    )
