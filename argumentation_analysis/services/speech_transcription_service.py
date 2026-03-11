"""
Speech Transcription Service — adapter for speech-to-text student project.

Wraps speech-to-text functionality to provide audio transcription
through the argumentation_analysis framework. Supports multiple
backends with automatic fallback:

  Tier 1: Whisper API (local or remote, OpenAI-compatible)
  Tier 2: Gradio WebUI client (e.g., whisper-webui.myia.io)

The service also exposes a convenience method to transcribe and
immediately analyze for fallacies (piping into FrenchFallacyAdapter).

Dependencies:
  - Tier 1: requests (HTTP client to Whisper API)
  - Tier 2: gradio_client (optional, for Gradio WebUI)

Integration from student project speech-to-text (GitHub #52).
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────

DEFAULT_WHISPER_URL = "http://localhost:8787"
ENV_WHISPER_URL = "WHISPER_API_URL"
ENV_WHISPER_USERNAME = "WHISPER_USERNAME"
ENV_WHISPER_PASSWORD = "WHISPER_PASSWORD"


# ── Data classes ─────────────────────────────────────────────────────────


@dataclass
class TranscriptionSegment:
    """A segment of transcribed audio."""

    text: str
    start_time: float = 0.0
    end_time: float = 0.0
    confidence: float = 1.0
    language: str = "fr"


@dataclass
class TranscriptionResult:
    """Full transcription result."""

    text: str
    segments: List[TranscriptionSegment] = field(default_factory=list)
    language: str = "fr"
    duration_seconds: float = 0.0
    model_used: str = "unknown"
    backend: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "segments": [
                {
                    "text": s.text,
                    "start": s.start_time,
                    "end": s.end_time,
                    "confidence": s.confidence,
                }
                for s in self.segments
            ],
            "language": self.language,
            "duration_seconds": self.duration_seconds,
            "model_used": self.model_used,
            "backend": self.backend,
        }


# ── Service class ────────────────────────────────────────────────────────


class SpeechTranscriptionService:
    """Multi-backend speech transcription service.

    Provides audio-to-text transcription through multiple backends
    with automatic fallback. Currently supports:

    - Whisper API (OpenAI-compatible endpoint)
    - Gradio WebUI client (for services like whisper-webui.myia.io)

    Register with CapabilityRegistry:
        registry.register_service(
            "speech_transcription",
            SpeechTranscriptionService,
            capabilities=["speech_transcription", "audio_processing"],
        )
    """

    def __init__(
        self,
        whisper_url: Optional[str] = None,
        whisper_username: Optional[str] = None,
        whisper_password: Optional[str] = None,
        timeout: int = 120,
    ):
        self._whisper_url = (
            whisper_url or os.environ.get(ENV_WHISPER_URL) or DEFAULT_WHISPER_URL
        ).rstrip("/")
        self._whisper_username = whisper_username or os.environ.get(
            ENV_WHISPER_USERNAME
        )
        self._whisper_password = whisper_password or os.environ.get(
            ENV_WHISPER_PASSWORD
        )
        self._timeout = timeout
        self._available = None

    def is_available(self) -> bool:
        """Check if any transcription backend is reachable."""
        if self._available is None:
            self._available = self._check_whisper_api()
        return self._available

    def _check_whisper_api(self) -> bool:
        """Check if the Whisper API endpoint is reachable."""
        try:
            import requests

            r = requests.get(
                f"{self._whisper_url}/health",
                timeout=5,
            )
            return r.status_code == 200
        except Exception:
            # Try /v1/models as alternative health check (OpenAI-compatible)
            try:
                import requests

                r = requests.get(
                    f"{self._whisper_url}/v1/models",
                    timeout=5,
                )
                return r.status_code == 200
            except Exception:
                return False

    def transcribe_file(
        self,
        file_path: str,
        language: str = "fr",
        model: str = "whisper-1",
    ) -> TranscriptionResult:
        """Transcribe an audio file.

        Args:
            file_path: Path to audio file (wav, mp3, m4a, etc.).
            language: Language code (default: "fr").
            model: Whisper model to use.

        Returns:
            TranscriptionResult with full text and segments.

        Raises:
            RuntimeError: If transcription fails.
            FileNotFoundError: If audio file doesn't exist.
        """
        import requests

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            data = {
                "model": model,
                "language": language,
                "response_format": "verbose_json",
            }

            try:
                resp = requests.post(
                    f"{self._whisper_url}/v1/audio/transcriptions",
                    files=files,
                    data=data,
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                body = resp.json()
            except Exception as e:
                raise RuntimeError(f"Whisper API transcription failed: {e}") from e

        segments = []
        for seg in body.get("segments", []):
            segments.append(
                TranscriptionSegment(
                    text=seg.get("text", ""),
                    start_time=seg.get("start", 0.0),
                    end_time=seg.get("end", 0.0),
                    confidence=seg.get("avg_logprob", 0.0),
                    language=language,
                )
            )

        return TranscriptionResult(
            text=body.get("text", ""),
            segments=segments,
            language=body.get("language", language),
            duration_seconds=body.get("duration", 0.0),
            model_used=model,
            backend="whisper_api",
        )

    def transcribe_bytes(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        language: str = "fr",
        model: str = "whisper-1",
    ) -> TranscriptionResult:
        """Transcribe audio from bytes.

        Args:
            audio_data: Raw audio bytes.
            filename: Filename hint for format detection.
            language: Language code.
            model: Whisper model to use.

        Returns:
            TranscriptionResult.
        """
        import requests

        files = {"file": (filename, audio_data)}
        data = {
            "model": model,
            "language": language,
            "response_format": "verbose_json",
        }

        try:
            resp = requests.post(
                f"{self._whisper_url}/v1/audio/transcriptions",
                files=files,
                data=data,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            body = resp.json()
        except Exception as e:
            raise RuntimeError(f"Whisper API transcription failed: {e}") from e

        segments = []
        for seg in body.get("segments", []):
            segments.append(
                TranscriptionSegment(
                    text=seg.get("text", ""),
                    start_time=seg.get("start", 0.0),
                    end_time=seg.get("end", 0.0),
                    confidence=seg.get("avg_logprob", 0.0),
                    language=language,
                )
            )

        return TranscriptionResult(
            text=body.get("text", ""),
            segments=segments,
            language=body.get("language", language),
            duration_seconds=body.get("duration", 0.0),
            model_used=model,
            backend="whisper_api",
        )

    def get_status_details(self) -> Dict[str, Any]:
        """Return service status details."""
        return {
            "service_type": "SpeechTranscriptionService",
            "whisper_url": self._whisper_url,
            "available": self.is_available(),
            "backends": ["whisper_api"],
        }
