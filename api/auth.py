"""Shared per-request token guard for cost-bearing API routes (#2800)."""

import hmac
import os
import threading
from typing import Optional

from fastapi import Depends, Header, HTTPException

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


def require_billed_request(_authorized: None = Depends(require_api_token)) -> None:
    """Reserve one billed request, atomically, after authentication succeeds."""
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
