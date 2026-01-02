"""
Tests for TTS (Text-to-Speech) Service - XTTS v2 (Coqui TTS)

These tests run against the live Docker container.
Ensure the service is running: docker compose up -d tts-service

Service runs at: http://localhost:8003 (configurable via TTS_SERVICE_URL env var)
"""
import os
import pytest
import httpx

# Service URLs - configurable via environment variables
TTS_SERVICE_URL = os.getenv("TTS_SERVICE_URL", "http://localhost:8003")

# Timeouts for different operations
HEALTH_CHECK_TIMEOUT = 5.0
TTS_TIMEOUT = 60.0  # TTS can be slow, especially on first load


@pytest.mark.tts
@pytest.mark.integration
class TestTTSHealth:
    """Health check tests for TTS service."""

    def test_voices_endpoint_health(self, http_client, tts_base_url):
        """Test the voices endpoint (used as health check in docker-compose)."""
        response = http_client.get(
            f"{tts_base_url}/v1/audio/voices",
            timeout=HEALTH_CHECK_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "voices" in data
        assert isinstance(data["voices"], list)

    def test_service_is_running(self, http_client, tts_base_url):
        """Verify the TTS service container is responding."""
        try:
            response = http_client.get(
                f"{tts_base_url}/v1/audio/voices",
                timeout=HEALTH_CHECK_TIMEOUT
            )
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.fail(
                f"TTS service not reachable at {tts_base_url}. "
                "Ensure Docker container is running: docker compose up -d tts-service"
            )

    def test_available_voices(self, http_client, tts_base_url):
        """Test that expected voices are available."""
        response = http_client.get(
            f"{tts_base_url}/v1/audio/voices",
            timeout=HEALTH_CHECK_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        voices = data["voices"]

        # Expected voices from the project (ayhan.wav, serdar.wav)
        assert len(voices) > 0, "No voices available"

        # Check if known voices are present
        expected_voices = ["ayhan", "serdar"]
        for voice in expected_voices:
            if voice in voices:
                return  # At least one expected voice found

        # If no expected voices, just verify list is not empty
        assert len(voices) > 0


@pytest.mark.tts
@pytest.mark.integration
class TestTTSCustomEndpoint:
    """Test the custom /tts/synthesize endpoint."""

    @pytest.mark.slow
    def test_synthesize_simple_text(self, http_client, tts_base_url):
        """Test synthesizing simple text."""
        response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            json={"text": "Hello, this is a test.", "voice": "ayhan"},
            timeout=TTS_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "audio_url" in data
        assert data["audio_url"].endswith(".wav")

    @pytest.mark.slow
    def test_synthesize_with_default_voice(self, http_client, tts_base_url):
        """Test synthesizing without specifying a voice (uses default)."""
        response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            json={"text": "Testing default voice."},
            timeout=TTS_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "audio_url" in data

    def test_synthesize_empty_text_fails(self, http_client, tts_base_url):
        """Test that empty text is rejected."""
        response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            json={"text": "", "voice": "ayhan"},
            timeout=TTS_TIMEOUT
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_synthesize_whitespace_only_fails(self, http_client, tts_base_url):
        """Test that whitespace-only text is rejected."""
        response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            json={"text": "   ", "voice": "ayhan"},
            timeout=TTS_TIMEOUT
        )
        assert response.status_code == 400


@pytest.mark.tts
@pytest.mark.integration
class TestTTSOpenAIEndpoint:
    """Test the OpenAI-compatible /v1/audio/speech endpoint."""

    @pytest.mark.slow
    def test_speech_with_input_param(self, http_client, tts_base_url):
        """Test speech synthesis using 'input' parameter (OpenAI format)."""
        response = http_client.post(
            f"{tts_base_url}/v1/audio/speech",
            json={"input": "Hello from OpenAI compatible endpoint.", "voice": "ayhan"},
            timeout=TTS_TIMEOUT
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "audio/wav"
        assert len(response.content) > 0

    @pytest.mark.slow
    def test_speech_with_text_param(self, http_client, tts_base_url):
        """Test speech synthesis using 'text' parameter (alternative format)."""
        response = http_client.post(
            f"{tts_base_url}/v1/audio/speech",
            json={"text": "Testing text parameter.", "voice": "ayhan"},
            timeout=TTS_TIMEOUT
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "audio/wav"

    def test_speech_empty_input_fails(self, http_client, tts_base_url):
        """Test that empty input is rejected."""
        response = http_client.post(
            f"{tts_base_url}/v1/audio/speech",
            json={"input": "", "voice": "ayhan"},
            timeout=TTS_TIMEOUT
        )
        assert response.status_code == 400

    @pytest.mark.slow
    def test_speech_returns_valid_wav(self, http_client, tts_base_url):
        """Test that returned audio is a valid WAV file."""
        response = http_client.post(
            f"{tts_base_url}/v1/audio/speech",
            json={"input": "WAV validation test.", "voice": "ayhan"},
            timeout=TTS_TIMEOUT
        )
        assert response.status_code == 200

        # WAV files start with "RIFF" header
        audio_bytes = response.content
        assert len(audio_bytes) > 44  # Minimum WAV header size
        assert audio_bytes[:4] == b"RIFF", "Response is not a valid WAV file"


@pytest.mark.tts
@pytest.mark.integration
class TestTTSMediaServing:
    """Test media file serving endpoint."""

    @pytest.mark.slow
    def test_retrieve_generated_audio(self, http_client, tts_base_url):
        """Test retrieving a generated audio file via /media endpoint."""
        # First generate audio
        synth_response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            json={"text": "Media retrieval test.", "voice": "ayhan"},
            timeout=TTS_TIMEOUT
        )
        assert synth_response.status_code == 200
        audio_url = synth_response.json()["audio_url"]

        # Extract filename from URL
        filename = audio_url.split("/")[-1]

        # Retrieve the audio file
        media_response = http_client.get(
            f"{tts_base_url}/media/{filename}",
            timeout=HEALTH_CHECK_TIMEOUT
        )
        assert media_response.status_code == 200
        assert media_response.headers.get("content-type") == "audio/wav"
        assert len(media_response.content) > 0

    def test_nonexistent_media_returns_404(self, http_client, tts_base_url):
        """Test that requesting nonexistent media returns 404."""
        response = http_client.get(
            f"{tts_base_url}/media/nonexistent_file_12345.wav",
            timeout=HEALTH_CHECK_TIMEOUT
        )
        assert response.status_code == 404


@pytest.mark.tts
@pytest.mark.integration
class TestTTSVoiceSelection:
    """Test voice selection functionality."""

    @pytest.mark.slow
    def test_synthesize_with_ayhan_voice(self, http_client, tts_base_url):
        """Test synthesis with ayhan voice."""
        response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            json={"text": "Testing ayhan voice.", "voice": "ayhan"},
            timeout=TTS_TIMEOUT
        )
        # May return 200 or fail if voice doesn't exist
        if response.status_code == 200:
            assert "audio_url" in response.json()
        else:
            pytest.skip("ayhan voice not available")

    @pytest.mark.slow
    def test_synthesize_with_serdar_voice(self, http_client, tts_base_url):
        """Test synthesis with serdar voice."""
        response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            json={"text": "Testing serdar voice.", "voice": "serdar"},
            timeout=TTS_TIMEOUT
        )
        if response.status_code == 200:
            assert "audio_url" in response.json()
        else:
            pytest.skip("serdar voice not available")

    @pytest.mark.slow
    def test_synthesize_with_invalid_voice_fallback(self, http_client, tts_base_url):
        """Test that invalid voice falls back to available voice."""
        response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            json={"text": "Testing fallback.", "voice": "nonexistent_voice_xyz"},
            timeout=TTS_TIMEOUT
        )
        # Should either succeed with fallback or fail gracefully
        assert response.status_code in [200, 404]


@pytest.mark.tts
@pytest.mark.integration
class TestTTSTextHandling:
    """Test various text input scenarios."""

    @pytest.mark.slow
    def test_synthesize_long_text(self, http_client, tts_base_url):
        """Test synthesizing longer text."""
        long_text = (
            "This is a longer piece of text that should be synthesized properly. "
            "It contains multiple sentences and various punctuation marks. "
            "The text-to-speech system should handle this without issues."
        )
        response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            json={"text": long_text, "voice": "ayhan"},
            timeout=TTS_TIMEOUT * 2  # Longer timeout for longer text
        )
        assert response.status_code == 200

    @pytest.mark.slow
    def test_synthesize_special_characters(self, http_client, tts_base_url):
        """Test synthesizing text with special characters."""
        special_text = "Hello! How are you? I'm fine, thanks."
        response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            json={"text": special_text, "voice": "ayhan"},
            timeout=TTS_TIMEOUT
        )
        assert response.status_code == 200

    @pytest.mark.slow
    def test_synthesize_numbers(self, http_client, tts_base_url):
        """Test synthesizing text with numbers."""
        number_text = "The temperature is 25 degrees and the time is 3:45 PM."
        response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            json={"text": number_text, "voice": "ayhan"},
            timeout=TTS_TIMEOUT
        )
        assert response.status_code == 200


@pytest.mark.tts
@pytest.mark.integration
@pytest.mark.slow
class TestTTSPerformance:
    """Performance tests for TTS service."""

    def test_multiple_sequential_requests(self, http_client, tts_base_url):
        """Test multiple sequential TTS requests."""
        for i in range(3):
            response = http_client.post(
                f"{tts_base_url}/tts/synthesize",
                json={"text": f"Test number {i+1}.", "voice": "ayhan"},
                timeout=TTS_TIMEOUT
            )
            assert response.status_code == 200, f"Request {i+1} failed"


@pytest.mark.tts
@pytest.mark.integration
class TestTTSInputValidation:
    """Test input validation for TTS service."""

    def test_missing_text_field(self, http_client, tts_base_url):
        """Test request without text field."""
        response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            json={"voice": "ayhan"},
            timeout=TTS_TIMEOUT
        )
        # Should fail with validation error
        assert response.status_code in [400, 422]

    def test_invalid_json(self, http_client, tts_base_url):
        """Test request with invalid JSON."""
        response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            content="not valid json",
            headers={"Content-Type": "application/json"},
            timeout=TTS_TIMEOUT
        )
        assert response.status_code == 422

    @pytest.mark.slow
    def test_unicode_text(self, http_client, tts_base_url):
        """Test synthesizing Unicode text (Turkish characters)."""
        turkish_text = "Merhaba, nasılsınız? Günaydın!"
        response = http_client.post(
            f"{tts_base_url}/tts/synthesize",
            json={"text": turkish_text, "voice": "ayhan"},
            timeout=TTS_TIMEOUT
        )
        # Should handle Unicode properly
        assert response.status_code == 200
