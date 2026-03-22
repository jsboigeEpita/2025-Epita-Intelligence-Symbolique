"""
Starlette routes for counter-argument generation.

Provides endpoints for parsing arguments, identifying vulnerabilities,
and generating counter-arguments using the 5 rhetorical strategies.
"""

import logging
import time

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger(__name__)


async def parse_argument(request: Request) -> JSONResponse:
    """POST /api/counter/parse — Parse an argument into premises and conclusion.

    Request body: {"text": "..."}
    Response: {"premises": [...], "conclusion": "...", "type": "..."}
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

    try:
        from argumentation_analysis.agents.core.counter_argument.parser import (
            ArgumentParser,
        )

        parser = ArgumentParser()
        result = parser.parse_argument(text)

        if isinstance(result, dict):
            return JSONResponse(result)
        return JSONResponse({"raw": str(result)})
    except ImportError:
        return JSONResponse(
            {"error": "Counter-argument module unavailable"}, status_code=503
        )
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def identify_vulnerabilities(request: Request) -> JSONResponse:
    """POST /api/counter/vulnerabilities — Identify argument vulnerabilities.

    Request body: {"text": "..."}
    Response: {"vulnerabilities": [...]}
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    text = body.get("text", "").strip()
    if not text:
        return JSONResponse({"error": "Text required"}, status_code=400)

    try:
        from argumentation_analysis.agents.core.counter_argument.parser import (
            ArgumentParser,
        )

        parser = ArgumentParser()
        vulns = parser.identify_vulnerabilities(text)
        return JSONResponse(
            {"vulnerabilities": vulns if isinstance(vulns, list) else [str(vulns)]}
        )
    except ImportError:
        return JSONResponse(
            {"error": "Counter-argument module unavailable"}, status_code=503
        )
    except Exception as e:
        logger.error(f"Vulnerability identification error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def list_strategies(request: Request) -> JSONResponse:
    """GET /api/counter/strategies — List available rhetorical strategies."""
    strategies = [
        {
            "name": "reductio_ad_absurdum",
            "description": "Show the argument leads to absurd conclusions",
        },
        {
            "name": "counter_example",
            "description": "Provide a concrete counter-example",
        },
        {
            "name": "distinction",
            "description": "Distinguish between cases the argument conflates",
        },
        {
            "name": "reformulation",
            "description": "Reformulate the argument to reveal hidden assumptions",
        },
        {
            "name": "concession",
            "description": "Concede partial validity while pivoting to a stronger position",
        },
    ]
    return JSONResponse({"strategies": strategies, "count": len(strategies)})


counter_argument_routes = [
    Route("/api/counter/parse", parse_argument, methods=["POST"]),
    Route("/api/counter/vulnerabilities", identify_vulnerabilities, methods=["POST"]),
    Route("/api/counter/strategies", list_strategies, methods=["GET"]),
]
