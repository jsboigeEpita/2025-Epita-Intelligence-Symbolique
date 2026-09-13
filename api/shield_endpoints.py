"""REST endpoint for AI Shield validation service (#842).

Exposes the AI Shield adversarial protection as a standalone API endpoint
for direct validation of text inputs.

Routes:
    POST /api/shield/validate — Validate text against adversarial patterns

Security:
    If SHIELD_ENDPOINT_TOKEN is set in the environment, callers must provide
    it via the X-Shield-Token header. If unset (dev mode), no auth required.
    This prevents unauthorized credit-drain on the OPENAI_API_KEY used by the
    shield's LLM-backed layers. See Hermes review concern on PR #874.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

shield_router = APIRouter(prefix="/shield", tags=["AI Shield"])

# ──── Auth guard ────

_SHIELD_TOKEN: Optional[str] = os.environ.get("SHIELD_ENDPOINT_TOKEN")
# NOTE: os.environ.get("OPENAI_API_KEY") is called per-request below because
# the key may rotate at runtime without restart. This is intentional.


def _verify_token(x_shield_token: Optional[str]) -> None:
    """Raise 401 if SHIELD_ENDPOINT_TOKEN is configured and token doesn't match."""
    if _SHIELD_TOKEN is None:
        return  # Dev mode — no auth required
    if x_shield_token != _SHIELD_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Shield-Token header")


# ──── Request/Response Models ────


class ShieldValidateRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to validate")
    preset: str = Field("basic", description="Shield preset: basic, advanced, output_only, strict")
    direction: str = Field("input", description="Validation direction: input or output")
    fail_open: Optional[bool] = Field(
        None,
        description=(
            "Pass if the shield fails to load. None (default) = the preset's "
            "declared policy — `strict` fails closed, the others fail open (#2144)"
        ),
    )


class LayerResultResponse(BaseModel):
    layer: str
    score: float
    passed: bool
    reason: str = ""


class ShieldValidateResponse(BaseModel):
    blocked: bool
    overall_score: float = 0.0
    passed: bool = True
    reason: str = ""
    layer_results: List[LayerResultResponse] = []
    shield_available: bool = True


# ──── Endpoint ────


@shield_router.post("/validate", response_model=ShieldValidateResponse)
async def shield_validate(
    request: ShieldValidateRequest,
    x_shield_token: Optional[str] = Header(None, alias="X-Shield-Token"),
):
    """Validate text against adversarial patterns using AI Shield.

    Requires X-Shield-Token header when SHIELD_ENDPOINT_TOKEN env var is set.
    """
    _verify_token(x_shield_token)

    try:
        from argumentation_analysis.services.ai_shield import (
            PRESET_FAIL_OPEN,
            load_preset,
        )
    except ImportError as exc:
        logger.warning(f"AI Shield not available: {exc}")
        # Paquet absent : aucune table de politique n'est lisible — cas non
        # tranché par #2144. On conserve le comportement d'origine (pass-through
        # sauf refus explicite), sans supposer la politique d'un preset.
        if request.fail_open is False:
            raise HTTPException(
                status_code=503, detail=f"AI Shield service unavailable: {exc}"
            )
        return ShieldValidateResponse(
            blocked=False,
            passed=True,
            shield_available=False,
            reason=f"Shield unavailable: {exc}",
        )

    api_key = os.environ.get("OPENAI_API_KEY")  # Per-request: key may rotate at runtime

    # Politique effective (#2144) : l'explicite prime, sinon la déclaration du
    # preset — même table que `load_preset`, source unique. Un `None` n'est plus
    # converti en `True` implicite : c'est ce qui faisait de `strict` une
    # politique fail-open sur cette porte.
    effective_fail_open = (
        request.fail_open
        if request.fail_open is not None
        else PRESET_FAIL_OPEN.get(request.preset, False)
    )

    try:
        shield = load_preset(
            request.preset, api_key=api_key, fail_open=request.fail_open
        )
    except Exception as exc:
        logger.error(f"Shield preset load failed: {exc}")
        if effective_fail_open:
            return ShieldValidateResponse(
                blocked=False,
                passed=True,
                shield_available=False,
                reason=f"Preset load failed: {exc}",
            )
        raise HTTPException(status_code=500, detail=f"Shield preset error: {exc}")

    try:
        if request.direction == "output":
            result = shield.validate_output(request.text)
        else:
            result = shield.validate_input(request.text)
    except Exception as exc:
        logger.error(f"Shield validation failed: {exc}")
        if request.fail_open:
            return ShieldValidateResponse(
                blocked=False,
                passed=True,
                shield_available=True,
                reason=f"Validation error: {exc}",
            )
        raise HTTPException(status_code=500, detail=f"Validation error: {exc}")

    return ShieldValidateResponse(
        blocked=result.blocked,
        overall_score=result.overall_score,
        passed=result.passed,
        reason=result.reason,
        layer_results=[
            LayerResultResponse(
                layer=lr.layer_name,
                score=lr.score,
                passed=lr.passed,
                reason=lr.reason,
            )
            for lr in result.layer_results
        ],
        shield_available=True,
    )
