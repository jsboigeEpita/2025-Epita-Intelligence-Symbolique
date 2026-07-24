"""Legible API error surface for the Democratech critical path.

DT-1 #1499 (anti-theater #1019): replace opaque HTTP 500 with typed,
machine-parseable error envelopes. The contract:

    {
        "error_code": "<machine-readable identifier>",
        "detail":     "<human-readable explanation>",
        "degraded":   <bool, true iff the request partially succeeded>,
        "context":    {<optional diagnostic key/value pairs>}
    }

Routes on the Democratech critical path (/analyze, /governance, /ws/*)
raise these instead of HTTPException. The global handler registered by
``install_error_handlers(app)`` translates them to the right HTTP status
(400 / 422 / 502 / 503 / 504) with the legible envelope.

Anti-pendule: we do NOT replace every HTTPException in the codebase —
only the routes the user-facing dashboard consumes. The other 30+ admin
endpoints keep their existing surface until DT-2/DT-3.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Base class for legible API errors on the Democratech critical path."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(
        self,
        detail: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        degraded: bool = False,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.context: Dict[str, Any] = context or {}
        self.degraded = degraded

    def to_envelope(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "detail": self.detail,
            "degraded": self.degraded,
            "context": self.context,
        }


class ValidationError(APIError):
    """The request payload is malformed or missing required fields."""

    status_code = 400
    error_code = "validation_error"


class UpstreamError(APIError):
    """An upstream service (LLM, JPype/Tweety, JTMS) failed unrecoverably.

    The downstream caller may want to surface a retry suggestion.
    """

    status_code = 502
    error_code = "upstream_error"


class TimeoutError_(APIError):
    """The pipeline exceeded its per-phase or per-request timeout.

    Note: this is APIError.TimeoutError_, not the builtin TimeoutError,
    to keep the import surface clean in route modules.
    """

    status_code = 504
    error_code = "timeout_error"


class DegradedError(APIError):
    """The pipeline returned a degraded result (some optional phase failed).

    Status 200 because the request DID return a verdict — but the
    ``degraded=True`` flag in the envelope and response body tells the
    consumer that not every capability resolved. Anti-theater: this is
    raised only when the orchestrator genuinely kept a degraded track,
    not as a catch-all for any 5xx.
    """

    status_code = 200
    error_code = "degraded_result"


class ServiceUnavailableError(APIError):
    """A required service is not booted (e.g. JVM init failed at startup)."""

    status_code = 503
    error_code = "service_unavailable"


def install_error_handlers(app: FastAPI) -> None:
    """Register global handlers that translate APIError -> JSONResponse."""

    @app.exception_handler(APIError)
    async def _api_error_handler(
        _request: Request, exc: APIError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_envelope(),
        )
