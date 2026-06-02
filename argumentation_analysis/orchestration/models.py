"""Data models for the orchestration layer.

Relocated from real_llm_orchestrator.py (deprecated shim, removed #885).
These dataclasses are used by service_manager.py for LLM analysis requests.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class LLMAnalysisRequest:
    """Structure for LLM analysis requests.

    Used by OrchestrationServiceManager to parameterize analysis calls.
    """

    text: str
    analysis_type: str
    context: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    timeout: int = 30


@dataclass
class LLMAnalysisResult:
    """Structure for LLM analysis results.

    Returned by analysis orchestration paths.
    """

    request_id: str
    analysis_type: str
    result: Dict[str, Any]
    confidence: float
    processing_time: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
