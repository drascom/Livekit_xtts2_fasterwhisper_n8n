"""
Tests for STT (Speech-to-Text) Service - Speaches (Faster-Whisper)

These tests run against the live Docker container.
Ensure the service is running: docker compose up -d stt-service

Service runs at: http://localhost:8000 (configurable via STT_SERVICE_URL env var)
"""
import os
import pytest
import httpx

# Service URLs - configurable via environment variables
STT_SERVICE_URL = os.getenv("STT_SERVICE_URL", "http://localhost:8000")

# Timeouts for different operations
HEALTH_CHECK_TIMEOUT = 5.0
TRANSCRIPTION_TIMEOUT = 30.0


@pytest.mark.stt
@pytest.mark.integration
class TestSTTHealth:
    """Health check tests for STT service."""

    def test_health_endpoint(self, http_client, stt_base_url):
        """Test that the STT service health endpoint is reachable."""
        response = http_client.get(
            f"{stt_base_url}/health",
            timeout=HEALTH_CHECK_TIMEOUT
        )
        assert response.status_code == 200
        # Speaches returns "OK" as plain text or JSON health status
        content = response.text.strip()
        assert content == "OK" or "status" in content

    def test_service_is_running(self, http_client, stt_base_url):
        """Verify the STT service container is responding."""
        try:
            response = http_client.get(
                f"{stt_base_url}/health",
                timeout=HEALTH_CHECK_TIMEOUT
            )
            assert response.status_code in [200, 404]  # Either health or root endpoint
        except httpx.ConnectError:
            pytest.fail(
                f"STT service not reachable at {stt_base_url}. "
                "Ensure Docker container is running: docker compose up -d stt-service"
            )


@pytest.mark.stt
@pytest.mark.integration
class TestSTTModels:
    """Test model discovery endpoints for STT service."""

    def test_list_models(self, http_client, stt_base_url):
        """Test listing available STT models (OpenAI-compatible endpoint)."""
        response = http_client.get(
            f"{stt_base_url}/v1/models",
            timeout=HEALTH_CHECK_TIMEOUT
        )
        # This endpoint may or may not exist depending on Speaches version
        if response.status_code == 200:
            data = response.json()
            assert "data" in data or "models" in data
        else:
            # Endpoint not available, which is acceptable
            pytest.skip("Models endpoint not available in this Speaches version")


@pytest.mark.stt
@pytest.mark.integration
class TestSTTTranscription:
    """Test transcription endpoints for STT service."""

    def test_transcribe_audio_file(self, http_client, stt_base_url, sample_audio_path):
        """Test transcribing an audio file using OpenAI-compatible endpoint."""
        with open(sample_audio_path, 'rb') as audio_file:
            files = {'file': ('audio.wav', audio_file, 'audio/wav')}
            data = {
                'model': 'Systran/faster-whisper-medium',
                'language': 'en',
            }

            response = http_client.post(
                f"{stt_base_url}/v1/audio/transcriptions",
                files=files,
                data=data,
                timeout=TRANSCRIPTION_TIMEOUT
            )

        assert response.status_code == 200
        result = response.json()
        assert 'text' in result
        assert isinstance(result['text'], str)

    def test_transcribe_with_response_format_json(self, http_client, stt_base_url, sample_audio_path):
        """Test transcription with JSON response format."""
        with open(sample_audio_path, 'rb') as audio_file:
            files = {'file': ('audio.wav', audio_file, 'audio/wav')}
            data = {
                'model': 'Systran/faster-whisper-medium',
                'response_format': 'json',
            }

            response = http_client.post(
                f"{stt_base_url}/v1/audio/transcriptions",
                files=files,
                data=data,
                timeout=TRANSCRIPTION_TIMEOUT
            )

        assert response.status_code == 200
        result = response.json()
        assert 'text' in result

    def test_transcribe_with_verbose_json(self, http_client, stt_base_url, sample_audio_path):
        """Test transcription with verbose JSON response format."""
        with open(sample_audio_path, 'rb') as audio_file:
            files = {'file': ('audio.wav', audio_file, 'audio/wav')}
            data = {
                'model': 'Systran/faster-whisper-medium',
                'response_format': 'verbose_json',
            }

            response = http_client.post(
                f"{stt_base_url}/v1/audio/transcriptions",
                files=files,
                data=data,
                timeout=TRANSCRIPTION_TIMEOUT
            )

        assert response.status_code == 200
        result = response.json()
        assert 'text' in result
        # Verbose JSON may include additional fields
        # like 'segments', 'language', 'duration'

    def test_transcribe_without_file_fails(self, http_client, stt_base_url):
        """Test that transcription fails without an audio file."""
        response = http_client.post(
            f"{stt_base_url}/v1/audio/transcriptions",
            data={'model': 'Systran/faster-whisper-medium'},
            timeout=TRANSCRIPTION_TIMEOUT
        )

        # Should fail with 4xx error
        assert response.status_code >= 400

    def test_transcribe_empty_file_handling(self, http_client, stt_base_url, tmp_path):
        """Test handling of empty audio file."""
        empty_file = tmp_path / "empty.wav"
        empty_file.write_bytes(b"")

        with open(empty_file, 'rb') as audio_file:
            files = {'file': ('empty.wav', audio_file, 'audio/wav')}
            data = {'model': 'Systran/faster-whisper-medium'}

            response = http_client.post(
                f"{stt_base_url}/v1/audio/transcriptions",
                files=files,
                data=data,
                timeout=TRANSCRIPTION_TIMEOUT
            )

        # Empty file should be rejected or return empty text
        # The exact behavior depends on the implementation
        # 415 = Unsupported Media Type (invalid WAV)
        assert response.status_code in [200, 400, 415, 422]


@pytest.mark.stt
@pytest.mark.integration
class TestSTTLanguageSupport:
    """Test language-specific transcription features."""

    def test_transcribe_with_english_language(self, http_client, stt_base_url, sample_audio_path):
        """Test transcription with explicit English language setting."""
        with open(sample_audio_path, 'rb') as audio_file:
            files = {'file': ('audio.wav', audio_file, 'audio/wav')}
            data = {
                'model': 'Systran/faster-whisper-medium',
                'language': 'en',
            }

            response = http_client.post(
                f"{stt_base_url}/v1/audio/transcriptions",
                files=files,
                data=data,
                timeout=TRANSCRIPTION_TIMEOUT
            )

        assert response.status_code == 200

    def test_transcribe_with_turkish_language(self, http_client, stt_base_url, sample_audio_path):
        """Test transcription with Turkish language setting (project uses Turkish voices)."""
        with open(sample_audio_path, 'rb') as audio_file:
            files = {'file': ('audio.wav', audio_file, 'audio/wav')}
            data = {
                'model': 'Systran/faster-whisper-medium',
                'language': 'tr',
            }

            response = http_client.post(
                f"{stt_base_url}/v1/audio/transcriptions",
                files=files,
                data=data,
                timeout=TRANSCRIPTION_TIMEOUT
            )

        assert response.status_code == 200


@pytest.mark.stt
@pytest.mark.integration
@pytest.mark.slow
class TestSTTPerformance:
    """Performance and load tests for STT service."""

    def test_multiple_sequential_transcriptions(self, http_client, stt_base_url, sample_audio_path):
        """Test multiple sequential transcription requests."""
        for i in range(3):
            with open(sample_audio_path, 'rb') as audio_file:
                files = {'file': ('audio.wav', audio_file, 'audio/wav')}
                data = {'model': 'Systran/faster-whisper-medium'}

                response = http_client.post(
                    f"{stt_base_url}/v1/audio/transcriptions",
                    files=files,
                    data=data,
                    timeout=TRANSCRIPTION_TIMEOUT
                )

            assert response.status_code == 200, f"Request {i+1} failed"


@pytest.mark.stt
@pytest.mark.integration
class TestSTTTranslation:
    """Test translation endpoint (if available)."""

    def test_translate_audio_to_english(self, http_client, stt_base_url, sample_audio_path):
        """Test audio translation to English (OpenAI-compatible endpoint)."""
        with open(sample_audio_path, 'rb') as audio_file:
            files = {'file': ('audio.wav', audio_file, 'audio/wav')}
            data = {
                'model': 'Systran/faster-whisper-medium',
            }

            response = http_client.post(
                f"{stt_base_url}/v1/audio/translations",
                files=files,
                data=data,
                timeout=TRANSCRIPTION_TIMEOUT
            )

        # Translation endpoint may not be available
        if response.status_code == 404:
            pytest.skip("Translation endpoint not available")

        assert response.status_code == 200
        result = response.json()
        assert 'text' in result
