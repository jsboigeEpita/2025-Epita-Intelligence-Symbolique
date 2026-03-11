"""REST endpoints optimized for the mobile application (3.1.5).

These endpoints provide a simplified interface that maps to the mobile app's
existing API contract (analyzeText, validateArgument, detectFallacies, chat).

Routes:
    POST /api/mobile/analyze     — Full argument analysis
    POST /api/mobile/fallacies   — Fallacy detection
    POST /api/mobile/validate    — Logical validation (Toulmin model)
    POST /api/mobile/chat        — Chat with AI assistant
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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
    overall_quality: float = 0.0


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


@mobile_router.post("/analyze", response_model=AnalyzeResponse)
async def mobile_analyze(request: TextRequest):
    """Analyze argumentative text — returns structured arguments."""
    import time

    start = time.time()
    try:
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        result = await run_unified_analysis(request.text, workflow_name="light")
        result_dict = result if isinstance(result, dict) else {"raw": str(result)}

        arguments = []
        for i, arg in enumerate(result_dict.get("identified_arguments", {}).items()):
            arg_id, desc = arg
            arguments.append(ArgumentResult(
                id=arg_id,
                text=desc,
                conclusion=desc,
            ))

        fallacies_raw = result_dict.get("identified_fallacies", {})
        if not arguments and result_dict.get("summary"):
            arguments.append(ArgumentResult(
                id="summary",
                text=result_dict["summary"],
                conclusion=result_dict.get("summary", ""),
            ))

        return AnalyzeResponse(
            text=request.text,
            arguments=arguments,
            overall_quality=result_dict.get("overall_quality", 0.5),
        )
    except Exception as e:
        logger.error(f"Mobile analyze failed: {e}")
        return AnalyzeResponse(
            text=request.text,
            arguments=[ArgumentResult(
                id="error",
                text=f"Analysis unavailable: {e}",
                conclusion=str(e),
            )],
            overall_quality=0.0,
        )


@mobile_router.post("/fallacies", response_model=FallacyResponse)
async def mobile_fallacies(request: TextRequest):
    """Detect logical fallacies in text."""
    import time

    start = time.time()
    try:
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        result = await run_unified_analysis(request.text, workflow_name="standard")
        result_dict = result if isinstance(result, dict) else {}

        fallacies = []
        for fid, fdata in result_dict.get("identified_fallacies", {}).items():
            if isinstance(fdata, dict):
                fallacies.append(FallacyInstance(
                    type=fdata.get("type", fid),
                    confidence=0.8,
                    explanation=fdata.get("justification", ""),
                ))

        return FallacyResponse(
            text=request.text,
            fallacies=fallacies,
            execution_time=time.time() - start,
        )
    except Exception as e:
        logger.error(f"Mobile fallacy detection failed: {e}")
        return FallacyResponse(
            text=request.text,
            fallacies=[],
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
                premises=[d.content if hasattr(d, "content") else str(d) for d in (toulmin.data or [])],
                conclusion=toulmin.claim or "",
                rule=toulmin.warrant or "",
            ),
            explanation=toulmin.qualifier or "Analysis complete",
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

        llm = create_llm_service()
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
        summary = result_dict.get("summary", result_dict.get("raw", "Analysis complete."))

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
