"""
Tests for SpeechTranscriptionService adapter (speech-to-text integration).

Tests validate:
- Module and class imports
- Data class creation (TranscriptionSegment, TranscriptionResult)
- Service initialization with defaults and custom config
- Availability check against Whisper API
- Transcription with mocked HTTP responses
- Error handling for missing files
- CapabilityRegistry registration
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestImports:
    """Test that service classes are importable."""

    def test_import_service(self):
        from argumentation_analysis.services.speech_transcription_service import (
            SpeechTranscriptionService,
        )

        assert SpeechTranscriptionService is not None

    def test_import_data_classes(self):
        from argumentation_analysis.services.speech_transcription_service import (
            TranscriptionSegment,
            TranscriptionResult,
        )

        assert TranscriptionSegment is not None
        assert TranscriptionResult is not None


class TestTranscriptionSegment:
    """Test TranscriptionSegment data class."""

    def test_creation(self):
        from argumentation_analysis.services.speech_transcription_service import (
            TranscriptionSegment,
        )

        seg = TranscriptionSegment(
            text="Bonjour", start_time=0.0, end_time=1.5, confidence=0.95
        )
        assert seg.text == "Bonjour"
        assert seg.start_time == 0.0
        assert seg.end_time == 1.5
        assert seg.language == "fr"

    def test_defaults(self):
        from argumentation_analysis.services.speech_transcription_service import (
            TranscriptionSegment,
        )

        seg = TranscriptionSegment(text="test")
        assert seg.start_time == 0.0
        assert seg.confidence == 1.0
        assert seg.language == "fr"


class TestTranscriptionResult:
    """Test TranscriptionResult data class."""

    def test_creation(self):
        from argumentation_analysis.services.speech_transcription_service import (
            TranscriptionResult,
            TranscriptionSegment,
        )

        result = TranscriptionResult(
            text="Bonjour le monde",
            segments=[
                TranscriptionSegment("Bonjour", 0.0, 0.8),
                TranscriptionSegment("le monde", 0.8, 1.5),
            ],
            duration_seconds=1.5,
            model_used="whisper-1",
            backend="whisper_api",
        )
        assert result.text == "Bonjour le monde"
        assert len(result.segments) == 2

    def test_to_dict(self):
        from argumentation_analysis.services.speech_transcription_service import (
            TranscriptionResult,
            TranscriptionSegment,
        )

        result = TranscriptionResult(
            text="Hello",
            segments=[TranscriptionSegment("Hello", 0.0, 1.0, 0.9)],
            duration_seconds=1.0,
            model_used="whisper-1",
            backend="whisper_api",
        )
        d = result.to_dict()
        assert d["text"] == "Hello"
        assert len(d["segments"]) == 1
        assert d["segments"][0]["text"] == "Hello"
        assert d["segments"][0]["confidence"] == 0.9
        assert d["model_used"] == "whisper-1"

    def test_empty_result(self):
        from argumentation_analysis.services.speech_transcription_service import (
            TranscriptionResult,
        )

        result = TranscriptionResult(text="")
        d = result.to_dict()
        assert d["text"] == ""
        assert d["segments"] == []
        assert d["backend"] == "unknown"


class TestServiceConfig:
    """Test service initialization and configuration."""

    def test_default_url(self):
        from argumentation_analysis.services.speech_transcription_service import (
            SpeechTranscriptionService,
        )

        svc = SpeechTranscriptionService()
        assert "8787" in svc._whisper_url

    def test_custom_url(self):
        from argumentation_analysis.services.speech_transcription_service import (
            SpeechTranscriptionService,
        )

        svc = SpeechTranscriptionService(whisper_url="http://my-whisper:9000")
        assert svc._whisper_url == "http://my-whisper:9000"

    def test_env_url(self):
        from argumentation_analysis.services.speech_transcription_service import (
            SpeechTranscriptionService,
        )

        with patch.dict(os.environ, {"WHISPER_API_URL": "http://env-whisper:9001"}):
            svc = SpeechTranscriptionService()
            assert svc._whisper_url == "http://env-whisper:9001"

    def test_credentials(self):
        from argumentation_analysis.services.speech_transcription_service import (
            SpeechTranscriptionService,
        )

        svc = SpeechTranscriptionService(
            whisper_username="user", whisper_password="pass"
        )
        assert svc._whisper_username == "user"
        assert svc._whisper_password == "pass"


class TestAvailability:
    """Test service availability check."""

    def test_unavailable_when_no_service(self):
        from argumentation_analysis.services.speech_transcription_service import (
            SpeechTranscriptionService,
        )

        svc = SpeechTranscriptionService(whisper_url="http://nonexistent:9999")
        assert svc.is_available() is False

    def test_available_with_health_endpoint(self):
        from argumentation_analysis.services.speech_transcription_service import (
            SpeechTranscriptionService,
        )

        svc = SpeechTranscriptionService()
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("requests.get", return_value=mock_response):
            svc._available = None
            assert svc.is_available() is True


class TestTranscription:
    """Test transcription with mocked HTTP."""

    def test_transcribe_bytes(self):
        from argumentation_analysis.services.speech_transcription_service import (
            SpeechTranscriptionService,
        )

        svc = SpeechTranscriptionService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "Bonjour le monde",
            "language": "fr",
            "duration": 2.5,
            "segments": [
                {"text": "Bonjour", "start": 0.0, "end": 0.8, "avg_logprob": -0.3},
                {"text": "le monde", "start": 0.8, "end": 2.5, "avg_logprob": -0.2},
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            result = svc.transcribe_bytes(b"fake audio data", "test.wav")

        assert result.text == "Bonjour le monde"
        assert len(result.segments) == 2
        assert result.duration_seconds == 2.5
        assert result.backend == "whisper_api"

    def test_transcribe_file_not_found(self):
        from argumentation_analysis.services.speech_transcription_service import (
            SpeechTranscriptionService,
        )

        svc = SpeechTranscriptionService()
        with pytest.raises(FileNotFoundError):
            svc.transcribe_file("/nonexistent/audio.wav")

    def test_transcribe_api_error(self):
        from argumentation_analysis.services.speech_transcription_service import (
            SpeechTranscriptionService,
        )

        svc = SpeechTranscriptionService()

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Error")

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Whisper API"):
                svc.transcribe_bytes(b"audio", "test.wav")


class TestStatusDetails:
    """Test status details reporting."""

    def test_status_details(self):
        from argumentation_analysis.services.speech_transcription_service import (
            SpeechTranscriptionService,
        )

        svc = SpeechTranscriptionService(whisper_url="http://test:8787")
        svc._available = True
        details = svc.get_status_details()
        assert details["service_type"] == "SpeechTranscriptionService"
        assert details["whisper_url"] == "http://test:8787"
        assert details["available"] is True


class TestCapabilityRegistration:
    """Test CapabilityRegistry integration."""

    def test_register_speech_transcription(self):
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.services.speech_transcription_service import (
            SpeechTranscriptionService,
        )

        registry = CapabilityRegistry()
        registry.register_service(
            "speech_transcription",
            SpeechTranscriptionService,
            capabilities=["speech_transcription", "audio_processing"],
        )
        services = registry.find_services_for_capability("speech_transcription")
        assert len(services) == 1
        assert services[0].name == "speech_transcription"
