"""REST endpoints optimized for the mobile application (3.1.5).

These endpoints provide a simplified interface that maps to the mobile app's
existing API contract (analyzeText, validateArgument, detectFallacies, chat).

Routes:
    POST /api/mobile/analyze     — Full argument analysis
    POST /api/mobile/fallacies   — Fallacy detection
    POST /api/mobile/validate    — Logical validation (Toulmin model)
    POST /api/mobile/chat        — Chat with AI assistant

#2541: ``/analyze`` and ``/fallacies`` answer only what ran. ``/fallacies`` is
the detector ``POST /api/fallacies`` serves; ``/analyze`` reads the state the
``light`` workflow writes. A run that did not happen fails with its reason
(the ``api/errors`` envelope) instead of answering 200 with an empty list.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .errors import ServiceUnavailableError, UnanalyzableInputError, UpstreamError
from .fallacy_detection import detect_fallacies

logger = logging.getLogger(__name__)

mobile_router = APIRouter(prefix="/mobile", tags=["Mobile API"])


# ──── Request/Response Models ────


class TextRequest(BaseModel):
    text: str = Field(..., min_length=5, description="Text to analyze")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")


class ArgumentResult(BaseModel):
    id: str
    text: str
    premises: List[str] = []
    conclusion: str = ""
    structure: str = "other"
    validity: bool = False
    fallacies: List[str] = []


class AnalyzeResponse(BaseModel):
    text: str
    arguments: List[ArgumentResult] = []
    # #2541: ``None`` when the quality phase measured none of the arguments.
    overall_quality: Optional[float] = None


class FallacyInstance(BaseModel):
    type: str
    confidence: float = 0.0
    span: List[int] = [0, 0]
    explanation: str = ""


class FallacyResponse(BaseModel):
    text: str
    fallacies: List[FallacyInstance] = []
    execution_time: float = 0.0


class ValidationFormalization(BaseModel):
    type: str = "other"
    premises: List[str] = []
    conclusion: str = ""
    rule: str = ""


class ValidateResponse(BaseModel):
    valid: bool = False
    formalization: ValidationFormalization = ValidationFormalization()
    explanation: str = ""
    execution_time: float = 0.0


class ChatResponse(BaseModel):
    message: str
    timestamp: str


# ──── Endpoints ────


# #2541: the ``extraction_status`` the fact extraction reports when it has no
# LLM client (``_invoke_fact_extraction``): the analysis did not run.
EXTRACTION_UNAVAILABLE = "failed:no-openai-client"


@mobile_router.post("/analyze", response_model=AnalyzeResponse)
async def mobile_analyze(request: TextRequest):
    """Analyze argumentative text — returns structured arguments.

    #2541: the arguments are the ones the ``light`` workflow writes to its
    state (``identified_arguments``), each as the extraction describes it: the
    pipeline does not split them into premises and a conclusion.
    ``overall_quality`` is the mean ``quality_fraction`` of the arguments the
    quality phase measured, ``None`` when it measured none.

    A run that did not happen fails with its reason: 503 when the extraction
    has no LLM client, 502 when the pipeline or the extraction failed, 422 when
    the pipeline classified the text as non-argumentative (an extraction that
    found no argument is one, #1909).
    """
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )
    from argumentation_analysis.plugins.narrative_synthesis_plugin import (
        quality_fraction,
    )

    context: Dict[str, Any] = {"workflow": "light"}
    try:
        result = await run_unified_analysis(request.text, workflow_name="light")
    except Exception as exc:
        raise UpstreamError(
            f"analysis pipeline: {type(exc).__name__}: {exc}", context=context
        ) from exc

    outcome = result.get("analysis_outcome") or {}
    context.update(outcome)
    if outcome.get("status") == "failed":
        reason = outcome.get("reason", "unknown")
        error = (
            ServiceUnavailableError
            if reason == EXTRACTION_UNAVAILABLE
            else UpstreamError
        )
        raise error(f"argument extraction: {reason}", context=context)
    if outcome.get("status") == "non_argumentative":
        raise UnanalyzableInputError(
            "The pipeline classified the text as non-argumentative: there is "
            "no argument to extract.",
            context=context,
        )
    state = result.get("unified_state")
    if state is None:
        raise UpstreamError(
            "analysis pipeline returned no state to read the arguments from",
            context=context,
        )

    arguments = [
        ArgumentResult(id=arg_id, text=description)
        for arg_id, description in state.identified_arguments.items()
    ]
    fractions = [
        quality_fraction(state.argument_quality_scores.get(arg_id))
        for arg_id in state.identified_arguments
    ]
    measured = [fraction for fraction in fractions if fraction is not None]
    return AnalyzeResponse(
        text=request.text,
        arguments=arguments,
        overall_quality=sum(measured) / len(measured) if measured else None,
    )


@mobile_router.post("/fallacies", response_model=FallacyResponse)
async def mobile_fallacies(request: TextRequest):
    """Detect logical fallacies in text.

    #2541: served by ``detect_fallacies``, the detector ``POST /api/fallacies``
    serves (the pipeline's own ``_invoke_hierarchical_fallacy``, ``llm`` tier),
    with the confidence it gives each detection. When it cannot run, the
    request fails with its reason (503 or 502); an empty list means it ran and
    found nothing. ``span`` locates the detector's quote in the text, and is
    ``[0, 0]`` when the quote cannot be located: the client highlights nothing.
    """
    import time

    from argumentation_analysis.agents.core.quality.passage import locate_quote

    start = time.time()
    detection = await detect_fallacies(request.text)
    fallacies = []
    for fallacy in detection.fallacies:
        span = locate_quote(request.text, fallacy.quote or "")
        fallacies.append(
            FallacyInstance(
                type=fallacy.name,
                confidence=fallacy.confidence,
                span=list(span) if span else [0, 0],
                explanation=fallacy.explanation or "",
            )
        )
    return FallacyResponse(
        text=request.text,
        fallacies=fallacies,
        execution_time=time.time() - start,
    )


@mobile_router.post("/validate", response_model=ValidateResponse)
async def mobile_validate(request: TextRequest):
    """Validate the logical structure of an argument."""
    import time

    start = time.time()
    try:
        from argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer import (
            SemanticArgumentAnalyzer,
        )

        analyzer = SemanticArgumentAnalyzer()
        toulmin = await analyzer.run(request.text)

        return ValidateResponse(
            valid=bool(toulmin.claim and toulmin.data),
            formalization=ValidationFormalization(
                type="toulmin",
                premises=[
                    d.text if hasattr(d, "text") else str(d)
                    for d in (toulmin.data or [])
                ],
                conclusion=toulmin.claim.text if toulmin.claim and hasattr(toulmin.claim, "text") else (str(toulmin.claim) if toulmin.claim else ""),
                rule=toulmin.warrant.text if toulmin.warrant and hasattr(toulmin.warrant, "text") else (str(toulmin.warrant) if toulmin.warrant else ""),
            ),
            explanation=toulmin.qualifier.text if toulmin.qualifier and hasattr(toulmin.qualifier, "text") else (str(toulmin.qualifier) if toulmin.qualifier else "Analysis complete"),
            execution_time=time.time() - start,
        )
    except Exception as e:
        logger.error(f"Mobile validation failed: {e}")
        return ValidateResponse(
            valid=False,
            explanation=f"Validation unavailable: {e}",
            execution_time=time.time() - start,
        )


@mobile_router.post("/chat", response_model=ChatResponse)
async def mobile_chat(request: ChatRequest):
    """Chat with AI assistant specialized in argument analysis."""
    from datetime import datetime

    try:
        from argumentation_analysis.core.llm_service import create_llm_service

        llm = create_llm_service(service_id="mobile_chat")
        if llm and hasattr(llm, "generate"):
            response = await llm.generate(
                f"You are an AI assistant specialized in analyzing arguments. "
                f"Provide clear, structured, and insightful responses.\n\n"
                f"User: {request.message}"
            )
            return ChatResponse(
                message=response,
                timestamp=datetime.utcnow().isoformat(),
            )
    except Exception as e:
        logger.warning(f"LLM chat failed, using fallback: {e}")

    # Fallback: use unified pipeline for analysis-style questions
    try:
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        result = await run_unified_analysis(request.message, workflow_name="light")
        result_dict = result if isinstance(result, dict) else {"raw": str(result)}
        summary = result_dict.get(
            "summary", result_dict.get("raw", "Analysis complete.")
        )

        return ChatResponse(
            message=summary,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Mobile chat failed completely: {e}")
        return ChatResponse(
            message="I'm unable to process your request at the moment. Please try again later.",
            timestamp=datetime.utcnow().isoformat(),
        )
