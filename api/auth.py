"""Shared per-request token guard for cost-bearing API routes (#2800)."""

import hmac
import os
import threading
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse

_TOKEN_ENV = "SHIELD_ENDPOINT_TOKEN"
_ANONYMOUS_ENV = "SHIELD_ALLOW_ANONYMOUS"
_TRUTHY = frozenset({"1", "true", "yes", "on"})
_BUDGET_ENV = "BILLED_REQUEST_BUDGET"
_DEFAULT_BUDGET = 1000
_budget_lock = threading.Lock()
_budget_used = 0


def require_api_token(
    x_shield_token: Optional[str] = Header(None, alias="X-Shield-Token"),
) -> None:
    """Read the configured token for each request, including after rotation."""
    token = os.environ.get(_TOKEN_ENV)
    if not token:
        if (os.environ.get(_ANONYMOUS_ENV) or "").strip().lower() in _TRUTHY:
            return
        raise HTTPException(
            status_code=503,
            detail=(
                f"API token is not configured: set {_TOKEN_ENV}, or set "
                f"{_ANONYMOUS_ENV}=1 to serve anonymously (development only)."
            ),
        )
    if x_shield_token is None or not hmac.compare_digest(x_shield_token, token):
        raise HTTPException(
            status_code=401, detail="Invalid or missing X-Shield-Token header"
        )


def require_billed_request(
    request: Request, _authorized: None = Depends(require_api_token)
) -> None:
    """Reserve one billed request, atomically, after authentication succeeds.

    The unit is released if FastAPI then rejects the body (#2820): an
    unaccepted request never invokes the service and bears no cost, and
    billing it would let a valid token exhaust the budget with malformed
    bodies alone. See ``refund_unaccepted_billed_request``.
    """
    global _budget_used
    configured = os.environ.get(_BUDGET_ENV, str(_DEFAULT_BUDGET))
    try:
        limit = int(configured)
    except ValueError:
        limit = 0
    if limit < 1:
        raise HTTPException(
            status_code=503, detail=f"Set {_BUDGET_ENV} to a positive integer"
        )
    with _budget_lock:
        if _budget_used >= limit:
            raise HTTPException(
                status_code=429, detail="Billed request budget exhausted"
            )
        _budget_used += 1
    request.state.billed_unit_reserved = True


async def refund_unaccepted_billed_request(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Release the reserved unit of a request the body validation rejected.

    Registered by ``create_app`` so the budget counts ACCEPTED cost-bearing
    requests, as DEPLOYMENT.md documents (#2820). Routes without the billed
    guard never set the flag, so a local route's 422 changes nothing.
    """
    if getattr(request.state, "billed_unit_reserved", False):
        global _budget_used
        with _budget_lock:
            _budget_used = max(0, _budget_used - 1)
    return await request_validation_exception_handler(request, exc)
