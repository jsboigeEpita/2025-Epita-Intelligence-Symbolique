"""What the OpenRouter key of this seat has spent, and what it has left.

    python scripts/panel/openrouter_credit.py

One GET on the provider's key endpoint; prints one JSON line with ``usage``,
``limit`` and ``limit_remaining`` (USD). A cycle reads it before the pipeline
and after the judges.

The provider's two counters are not two views of one budget. On the cycles
recorded in November 2026 the credit fell by about 10 USD over a cycle while
``usage`` moved by about 0.3 USD, and on one paid run ``usage`` did not move
at all while the credit fell by 0.42 USD. The cycle's spend is therefore the
FALL of ``limit_remaining``; the change of ``usage`` is recorded beside it,
under its own name, and the record says when the two disagree by more than a
stated margin. What the provider means by ``usage`` is not established from
here: the two readings are reported, they are not adjudicated.

``limit_remaining`` is also the figure that decides whether a cycle can start:
with the key at its spending limit, neither the pipeline nor an OpenRouter
judge can run (met on 2026-11-07). An Anthropic judge is billed on another key
and does not appear here.

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

# The two provider counters disagree by more than this and the record says so:
# a quarter of the larger figure, and never less than five cents.
DISAGREEMENT_MARGIN = 0.25
DISAGREEMENT_FLOOR_USD = 0.05

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


def usage_delta_between(
    before: Optional[Dict[str, Any]], after: Optional[Dict[str, Any]]
) -> Optional[float]:
    """The change of the provider's ``usage`` counter between two readings
    (after minus before), or ``None`` when either reading is missing."""
    try:
        return round(float(after["usage"]) - float(before["usage"]), 4)  # type: ignore[index]
    except (TypeError, KeyError, ValueError):
        return None


def spent_between(
    before: Optional[Dict[str, Any]], after: Optional[Dict[str, Any]]
) -> Optional[float]:
    """The change of the provider's ``usage`` counter between two readings, or
    ``None`` when either reading is missing — an unread credit is not a zero
    spend.

    This is NOT what the cycle spent: on the cycles of November 2026 the
    counter moved by a fraction of what the credit fell by, and on one paid
    run it did not move at all (#3561). The spend is
    ``credit_fall_between``; this function is kept for the readers that
    already call it and want the counter's own change.
    """
    return usage_delta_between(before, after)


def limit_remaining_delta_between(
    before: Optional[Dict[str, Any]], after: Optional[Dict[str, Any]]
) -> Optional[float]:
    """The change of the provider's ``limit_remaining`` between two readings
    (after minus before — negative when the credit fell), or ``None`` when
    either reading is missing."""
    try:
        return round(
            float(after["limit_remaining"]) - float(before["limit_remaining"]), 4  # type: ignore[index]
        )
    except (TypeError, KeyError, ValueError):
        return None


def credit_fall_between(
    before: Optional[Dict[str, Any]], after: Optional[Dict[str, Any]]
) -> Optional[float]:
    """USD the credit fell by between two readings — the fall of the
    provider's ``limit_remaining`` — or ``None`` when either reading is
    missing: an unread credit is not a zero spend.

    This is the cycle's spend, as the provider's own budget reports it. It is
    not a token count multiplied by a price table.
    """
    delta = limit_remaining_delta_between(before, after)
    if delta is None:
        return None
    fall = round(-delta, 4)
    # A credit that did not move fell by zero, not by minus zero.
    return fall + 0.0


def spend_disagreement(
    usage_spend: Optional[float], credit_spend: Optional[float]
) -> Optional[bool]:
    """Whether the provider's two counters disagree by more than the stated
    margin: a quarter of the larger figure, and never less than five cents.

    ``None`` when one of the two is missing — an unread figure is not an
    agreement.
    """
    if usage_spend is None or credit_spend is None:
        return None
    usage_spend, credit_spend = abs(usage_spend), abs(credit_spend)
    difference = abs(usage_spend - credit_spend)
    margin = max(
        DISAGREEMENT_FLOOR_USD, DISAGREEMENT_MARGIN * max(usage_spend, credit_spend)
    )
    return difference > margin


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
