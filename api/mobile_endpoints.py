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

#2688: the same holds for ``/validate`` and ``/chat``. An analyzer or a chat
model that did not answer is a non-2xx answer, never a verdict (``valid:
false``) or a canned sentence; and ``/analyze`` no longer presents a validity
or a structure that nothing decides.
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
    # #2688: ``None`` = undecided. The ``light`` workflow decides neither the
    # structure nor the validity of an argument; a default here would be
    # presented as a verdict.
    structure: Optional[str] = None
    validity: Optional[bool] = None
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
    if outcome.get("status") in ("blocked", "skipped"):
        raise UpstreamError(
            f"argument extraction did not run: {outcome.get('reason', 'unknown')}",
            context=context,
        )
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


def _endpoint_unreachable(exc: BaseException) -> bool:
    """Whether ``exc`` comes from a model endpoint that refused the connection.

    #2688: the Toulmin analyzer's model is self-hosted; when nothing serves it
    the OpenAI client raises ``APIConnectionError``, which Semantic Kernel wraps
    twice (measured: ``KernelInvokeException`` > ``FunctionExecutionException``
    > ``ServiceResponseException`` > ``openai.APIConnectionError``).
    """
    from openai import APIConnectionError

    seen = set()
    while exc is not None and id(exc) not in seen:
        if isinstance(exc, APIConnectionError):
            return True
        seen.add(id(exc))
        exc = exc.__cause__ or exc.__context__
    return False


@mobile_router.post("/validate", response_model=ValidateResponse)
async def mobile_validate(request: TextRequest):
    """Validate the logical structure of an argument.

    ``valid`` is true when the Toulmin analyzer found a claim and the data
    supporting it.

    #2688: a failure of the analyzer is not a verdict on the argument: 503 when
    its model is not served (the connection is refused), 502 when it answered
    and the analysis failed.
    """
    import time

    from argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer import (
        SemanticArgumentAnalyzer,
    )

    start = time.time()
    context: Dict[str, Any] = {"analyzer": "SemanticArgumentAnalyzer"}
    try:
        toulmin = await SemanticArgumentAnalyzer().run(request.text)
    except Exception as exc:
        error = ServiceUnavailableError if _endpoint_unreachable(exc) else UpstreamError
        raise error(
            f"Toulmin analyzer: {type(exc).__name__}: {exc}", context=context
        ) from exc

    return ValidateResponse(
        valid=bool(toulmin.claim and toulmin.data),
        formalization=ValidationFormalization(
            type="toulmin",
            premises=[
                d.text if hasattr(d, "text") else str(d) for d in (toulmin.data or [])
            ],
            conclusion=(
                toulmin.claim.text
                if toulmin.claim and hasattr(toulmin.claim, "text")
                else (str(toulmin.claim) if toulmin.claim else "")
            ),
            rule=(
                toulmin.warrant.text
                if toulmin.warrant and hasattr(toulmin.warrant, "text")
                else (str(toulmin.warrant) if toulmin.warrant else "")
            ),
        ),
        explanation=(
            toulmin.qualifier.text
            if toulmin.qualifier and hasattr(toulmin.qualifier, "text")
            else (str(toulmin.qualifier) if toulmin.qualifier else "Analysis complete")
        ),
        execution_time=time.time() - start,
    )


CHAT_SYSTEM_PROMPT = (
    "You are an AI assistant specialized in analyzing arguments. "
    "Provide clear, structured, and insightful responses."
)


@mobile_router.post("/chat", response_model=ChatResponse)
async def mobile_chat(request: ChatRequest):
    """Chat with AI assistant specialized in argument analysis.

    #2688: the answer is the chat model's reply, asked through the Semantic
    Kernel service ``create_llm_service`` builds. 503 when no chat model can be
    configured (no API key), 502 when the call fails or the reply is empty.
    There is no pipeline fallback: the analysis pipeline produces no reply to a
    message.
    """
    from datetime import datetime

    from semantic_kernel.connectors.ai.prompt_execution_settings import (
        PromptExecutionSettings,
    )
    from semantic_kernel.contents import ChatHistory

    from argumentation_analysis.core.llm_service import create_llm_service

    context: Dict[str, Any] = {"service_id": "mobile_chat"}
    try:
        llm = create_llm_service(service_id="mobile_chat")
    except (ValueError, RuntimeError) as exc:
        raise ServiceUnavailableError(f"chat model: {exc}", context=context) from exc

    history = ChatHistory(system_message=CHAT_SYSTEM_PROMPT)
    history.add_user_message(request.message)
    try:
        reply = await llm.get_chat_message_content(
            chat_history=history, settings=PromptExecutionSettings()
        )
    except Exception as exc:
        raise UpstreamError(
            f"chat model: {type(exc).__name__}: {exc}", context=context
        ) from exc

    message = str(reply).strip() if reply is not None else ""
    if not message:
        raise UpstreamError("chat model returned an empty reply", context=context)
    return ChatResponse(message=message, timestamp=datetime.utcnow().isoformat())
