"""Shared JSON-object input parsing for ``@kernel_function`` entry points.

#1773 constat 4 (amendement R819): this is a REUSABLE convention — TweetyLogicPlugin's
21 functions (#1774) must adopt the same error shape, not a local variant. Rules:

- anything that is not a JSON object renders a structured error, never raises;
- a missing required key names the keys received AND the keys expected, so a
  caller that sent the wrong shape can converge by retry.
"""

import json
from typing import Any, Dict, Optional, Sequence, Tuple


def parse_kernel_json_object(
    raw: Any,
    expected_keys: Sequence[str],
    required_keys: Sequence[str] = (),
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Parse a ``@kernel_function`` JSON input into an object.

    Returns ``(params, None)`` when ``raw`` is a usable JSON object, otherwise
    ``(None, error_dict)`` where ``error_dict`` is ready to ``json.dumps``.
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None, {"error": "Invalid JSON input"}
    if not isinstance(raw, dict):
        return None, {
            "error": "Invalid input: expected a JSON object",
            "received_type": type(raw).__name__,
        }
    missing = [key for key in required_keys if key not in raw]
    if missing:
        return None, {
            "error": "Missing required key(s): " + ", ".join(missing),
            "received_keys": sorted(raw.keys()),
            "expected_keys": list(expected_keys),
        }
    return raw, None
