"""Shared per-request token guard for cost-bearing API routes (#2800)."""

import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException

_TOKEN_ENV = "SHIELD_ENDPOINT_TOKEN"
_ANONYMOUS_ENV = "SHIELD_ALLOW_ANONYMOUS"
_TRUTHY = frozenset({"1", "true", "yes", "on"})


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
