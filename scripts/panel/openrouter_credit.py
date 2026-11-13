"""What the OpenRouter key of this seat has spent, and what it has left.

    python scripts/panel/openrouter_credit.py

One GET on the provider's key endpoint; prints one JSON line with ``usage``,
``limit`` and ``limit_remaining`` (USD). A cycle reads it before the pipeline
and after the judges: the difference is what the cycle spent on that key, read
from the provider and not from a token count multiplied by a price table.

``limit_remaining`` is the figure that decides whether a cycle can start: with
the key at its spending limit, neither the pipeline nor an OpenRouter judge
can run (met on 2026-11-07). An Anthropic judge is billed on another key and
does not appear here.

The key is the one the pipeline would use: the value the process was started
with, else the checkout's ``.env``. It is never printed.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.panel import _common as c  # noqa: E402

KEY_URL = "https://openrouter.ai/api/v1/key"
KEY_VARIABLE = "OPENROUTER_API_KEY"
FIELDS = ("usage", "limit", "limit_remaining")

Fetch = Callable[[str], Dict[str, Any]]


class CreditUnavailable(RuntimeError):
    """The credit could not be read; the message never carries the key."""


def resolve_key(dotenv_path: Optional[Path] = None) -> Tuple[str, str]:
    """``(key, source)`` — the process's value, else the checkout's ``.env``.

    The source is ``process`` only for a value the ``.env`` does not hold.
    The package's loader copies the ``.env`` into the process at import, so
    "the variable is set in the process" does not tell the two apart; the
    comparison does, and a key that shadows the checkout's is the case worth
    seeing.
    """
    from dotenv import dotenv_values

    path = Path(dotenv_path) if dotenv_path is not None else c.REPO_ROOT / ".env"
    file_values = dotenv_values(path) if path.is_file() else {}
    file_key = (file_values.get(KEY_VARIABLE) or "").strip()
    process_key = (os.environ.get(KEY_VARIABLE) or "").strip()
    if process_key and process_key != file_key:
        return process_key, "process"
    return file_key, ".env"


def http_fetch(key: str, timeout: int = 30) -> Dict[str, Any]:
    """The provider's answer for ``key`` (the ``data`` object)."""
    request = urllib.request.Request(
        KEY_URL, headers={"Authorization": "Bearer " + key}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raise CreditUnavailable(f"the key endpoint answered {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise CreditUnavailable(
            f"the key endpoint is unreachable ({type(exc).__name__})"
        ) from None
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise CreditUnavailable("the key endpoint answered without a data object")
    return data


def read_credit(
    fetch: Fetch = http_fetch, dotenv_path: Optional[Path] = None
) -> Dict[str, Any]:
    """``usage`` / ``limit`` / ``limit_remaining`` and where the key came from."""
    key, source = resolve_key(dotenv_path)
    if not key:
        raise CreditUnavailable(
            f"{KEY_VARIABLE} is set neither in the process nor in the checkout's .env"
        )
    data = fetch(key)
    return {**{field: data.get(field) for field in FIELDS}, "key_source": source}


def spent_between(
    before: Optional[Dict[str, Any]], after: Optional[Dict[str, Any]]
) -> Optional[float]:
    """USD spent on the key between two readings, or ``None`` when either
    reading is missing — an unread credit is not a zero spend."""
    try:
        return round(float(after["usage"]) - float(before["usage"]), 4)  # type: ignore[index]
    except (TypeError, KeyError, ValueError):
        return None


def main(argv: Optional[List[str]] = None) -> int:
    try:
        credit = read_credit()
    except CreditUnavailable as exc:
        print(f"credit unavailable: {exc}")
        return 1
    print(json.dumps(credit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
