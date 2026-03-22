"""
Starlette routes for argument quality evaluation.

Provides endpoints for evaluating the quality of arguments using
the 9-virtue ArgumentQualityEvaluator.
"""

import logging
import time

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger(__name__)

_evaluator = None


def _get_evaluator():
    """Lazy-load the ArgumentQualityEvaluator."""
    global _evaluator
    if _evaluator is None:
        try:
            from argumentation_analysis.agents.core.quality.quality_evaluator import (
                ArgumentQualityEvaluator,
            )

            _evaluator = ArgumentQualityEvaluator()
            logger.info("ArgumentQualityEvaluator loaded successfully")
        except Exception as e:
            logger.warning(f"ArgumentQualityEvaluator unavailable: {e}")
    return _evaluator


async def evaluate_quality(request: Request) -> JSONResponse:
    """POST /api/quality — Evaluate argument quality (9 virtues).

    Request body: {"text": "..."}
    Response: {"text": "...", "scores": {...}, "overall": ..., "virtues": [...]}
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
    evaluator = _get_evaluator()

    if evaluator is None:
        return JSONResponse(
            {"error": "Quality evaluator unavailable"}, status_code=503
        )

    try:
        result = evaluator.evaluate(text)
        elapsed = time.time() - start

        if isinstance(result, dict):
            return JSONResponse(
                {
                    "text": text[:200],
                    "scores": result.get("scores_par_vertu", result.get("scores", {})),
                    "overall": result.get("score_global", result.get("overall", 0.0)),
                    "average": result.get("score_moyen", 0.0),
                    "report": result.get("rapport", ""),
                    "execution_time": round(elapsed, 3),
                }
            )
        return JSONResponse(
            {"text": text[:200], "result": str(result), "execution_time": round(elapsed, 3)}
        )
    except Exception as e:
        logger.error(f"Quality evaluation error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def list_virtues(request: Request) -> JSONResponse:
    """GET /api/quality/virtues — List the 9 argumentative virtues."""
    virtues = [
        {"name": "clarte", "description": "Clarity — Flesch readability score"},
        {"name": "pertinence", "description": "Relevance — topic alignment"},
        {"name": "sources", "description": "Source citations present"},
        {"name": "refutation", "description": "Constructive refutation"},
        {"name": "structure_logique", "description": "Logical structure (connectors)"},
        {"name": "analogies", "description": "Analogies used"},
        {"name": "fiabilite_sources", "description": "Source reliability"},
        {"name": "exhaustivite", "description": "Exhaustiveness"},
        {"name": "faible_redundance", "description": "Low redundancy"},
    ]
    return JSONResponse({"virtues": virtues, "count": len(virtues)})


quality_routes = [
    Route("/api/quality", evaluate_quality, methods=["POST"]),
    Route("/api/quality/virtues", list_virtues, methods=["GET"]),
]
