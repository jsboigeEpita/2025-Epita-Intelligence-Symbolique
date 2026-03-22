"""
Starlette routes for fallacy detection.

Provides endpoints for detecting argumentative fallacies in text using
the FrenchFallacyAdapter (3-tier: symbolic -> NLI -> LLM).
"""

import json
import logging
import time

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger(__name__)

_adapter = None


def _get_adapter():
    """Lazy-load the FrenchFallacyAdapter."""
    global _adapter
    if _adapter is None:
        try:
            from argumentation_analysis.adapters.french_fallacy_adapter import (
                FrenchFallacyAdapter,
            )

            _adapter = FrenchFallacyAdapter()
            logger.info("FrenchFallacyAdapter loaded successfully")
        except Exception as e:
            logger.warning(f"FrenchFallacyAdapter unavailable: {e}")
    return _adapter


async def detect_fallacies(request: Request) -> JSONResponse:
    """POST /api/fallacies — Detect fallacies in text.

    Request body: {"text": "..."}
    Response: {"text": "...", "fallacies": [...], "execution_time": ...}
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    text = body.get("text", "").strip()
    if not text or len(text) < 10:
        return JSONResponse(
            {"error": "Text must be at least 10 characters"}, status_code=400
        )

    start = time.time()
    adapter = _get_adapter()

    if adapter is None:
        return JSONResponse(
            {"error": "Fallacy detection service unavailable"}, status_code=503
        )

    try:
        result = adapter.detect(text)
        elapsed = time.time() - start

        fallacies = []
        if isinstance(result, list):
            for f in result:
                if isinstance(f, dict):
                    fallacies.append(
                        {
                            "type": f.get("fallacy_type", f.get("type", "unknown")),
                            "confidence": f.get("confidence", 0.0),
                            "explanation": f.get("explanation", ""),
                            "tier": f.get("detection_tier", "unknown"),
                        }
                    )

        return JSONResponse(
            {
                "text": text[:200],
                "fallacies": fallacies,
                "count": len(fallacies),
                "execution_time": round(elapsed, 3),
            }
        )
    except Exception as e:
        logger.error(f"Fallacy detection error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def list_fallacy_types(request: Request) -> JSONResponse:
    """GET /api/fallacies/types — List available fallacy types."""
    try:
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FALLACY_LABELS_FR,
        )

        return JSONResponse(
            {"types": FALLACY_LABELS_FR, "count": len(FALLACY_LABELS_FR)}
        )
    except ImportError:
        return JSONResponse({"types": [], "count": 0, "error": "Adapter unavailable"})


fallacy_routes = [
    Route("/api/fallacies", detect_fallacies, methods=["POST"]),
    Route("/api/fallacies/types", list_fallacy_types, methods=["GET"]),
]
