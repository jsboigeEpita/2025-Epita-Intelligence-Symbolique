"""The one fallacy detector the API serves (#2526).

``POST /api/fallacies`` and the ``fallacies`` of ``POST /api/analyze`` both call
``_invoke_hierarchical_fallacy``, the function the pipeline's fallacy phase
calls, with the tier the request names (``llm`` by default). The API therefore
answers what the pipeline answers.

An empty ``fallacies`` list means the detector ran and found nothing. When it
did not run, the request fails and says why; it never answers ``200`` with an
empty list:

- 503 when the tier has no detector: no LLM key (the detector raises
  ``FALLACY_DETECTION_UNAVAILABLE``), no taxonomy file, a missing dependency;
- 502 when the detector ran and failed: the invoker raises
  ``FallacyDetectionFailed`` (``FALLACY_DETECTION_FAILED: ...``) when none of
  its LLM runs answered (#2540), and any other exception is a failure too.

Each detected fallacy carries what the detector says about it (name, family,
explanation, the passage it quotes) and, from the taxonomy row of its
``taxonomy_pk``, the description and an example, in French: the CSV the
detector itself navigates.
"""

import csv
import functools
import os
import time
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .errors import ServiceUnavailableError, UpstreamError

FallacyTier = Literal["taxonomy", "hybrid", "llm", "full"]

TAXONOMY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "argumentation_analysis",
    "data",
    "argumentum_fallacies_taxonomy.csv",
)

# Result markers of a tier that did not run: ``_invoke_taxonomy_only_fallacy``
# and ``_invoke_hybrid_fallacy`` return them instead of raising.
_NOT_RUN = {"skipped", "unavailable"}


class FallacyDetectionOptions(BaseModel):
    """What the detector takes. Any other key is refused, not ignored."""

    model_config = ConfigDict(extra="forbid")

    tier: FallacyTier = Field(
        default="llm",
        description="Detection depth, as the pipeline's ``fallacy_tier``.",
    )
    min_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Detections below this confidence are counted, not listed.",
    )


class FallacyDetectionRequest(BaseModel):
    text: str = Field(..., min_length=1)
    options: FallacyDetectionOptions = Field(default_factory=FallacyDetectionOptions)

    @field_validator("text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text is blank")
        return value.strip()


class DetectedFallacy(BaseModel):
    name: str
    confidence: float
    taxonomy_pk: Optional[str] = None
    family: Optional[str] = None
    description: Optional[str] = None
    example: Optional[str] = None
    explanation: Optional[str] = None
    quote: Optional[str] = None


class FallacyDetectionResponse(BaseModel):
    tier: str
    fallacies: List[DetectedFallacy]
    fallacy_count: int
    below_threshold: int = Field(
        description="Detections dropped by ``min_confidence``; 0 when none were."
    )
    method: Optional[str] = Field(
        default=None, description="The detector's ``extraction_method``."
    )
    degraded: bool = False
    degradation_reason: Optional[str] = Field(
        default=None, description="The detector's ``last_error`` when degraded."
    )
    processing_time: float


@functools.lru_cache(maxsize=1)
def _taxonomy_rows() -> Dict[str, Dict[str, str]]:
    """``{PK: row}`` of the taxonomy CSV, read once."""
    from argumentation_analysis.utils.taxonomy_local_overrides import purge_rows

    with open(TAXONOMY_PATH, encoding="utf-8") as handle:
        rows = purge_rows(list(csv.DictReader(handle)))
    return {str(row.get("PK", "")).strip(): row for row in rows}


def _described(item: Dict[str, Any]) -> DetectedFallacy:
    pk = str(item.get("taxonomy_pk") or "").strip() or None
    row = _taxonomy_rows().get(pk, {}) if pk else {}
    name = item.get("fallacy_type") or item.get("type") or row.get("text_fr")
    return DetectedFallacy(
        name=str(name or "unknown"),
        confidence=float(item.get("confidence") or 0.0),
        taxonomy_pk=pk,
        family=item.get("family") or row.get("Famille") or None,
        description=row.get("desc_fr") or item.get("description") or None,
        example=row.get("example_fr") or None,
        explanation=item.get("explanation") or None,
        quote=item.get("problematic_quote") or None,
    )


async def detect_fallacies(
    text: str, tier: str = "llm", min_confidence: float = 0.0
) -> FallacyDetectionResponse:
    """The pipeline's detector on ``text``; raises an ``APIError`` when it did not run."""
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_hierarchical_fallacy,
    )

    started = time.monotonic()
    context = {"tier": tier}
    try:
        result = await _invoke_hierarchical_fallacy(text, {"fallacy_tier": tier})
    except RuntimeError as exc:
        if str(exc).startswith("FALLACY_DETECTION_UNAVAILABLE"):
            raise ServiceUnavailableError(str(exc), context=context) from exc
        raise UpstreamError(f"fallacy detector: {exc}", context=context) from exc
    except Exception as exc:
        raise UpstreamError(
            f"fallacy detector: {type(exc).__name__}: {exc}", context=context
        ) from exc

    method = result.get("extraction_method") or result.get("exploration_method")
    if method in _NOT_RUN:
        reason = result.get("error") or result.get("reason") or method
        raise ServiceUnavailableError(
            f"FALLACY_DETECTION_UNAVAILABLE: tier={tier}, reason={reason}",
            context=context,
        )
    found = [_described(item) for item in result.get("fallacies") or []]
    kept = [f for f in found if f.confidence >= min_confidence]
    return FallacyDetectionResponse(
        tier=tier,
        fallacies=kept,
        fallacy_count=len(kept),
        below_threshold=len(found) - len(kept),
        method=method,
        degraded=bool(result.get("degraded")),
        degradation_reason=result.get("last_error") if result.get("degraded") else None,
        processing_time=round(time.monotonic() - started, 3),
    )
