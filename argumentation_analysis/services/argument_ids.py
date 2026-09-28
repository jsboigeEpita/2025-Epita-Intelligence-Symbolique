"""Shared ``arg_N`` identifier conventions (#1629, #1633, #2744).

Single owner of the fallacy-target resolution helpers. Both the orchestration
layer (``invoke_callables``) and the service layer
(``semantic_index_service``) resolve fallacy targets through this module —
re-stating the convention in a second copy made the copies drift (an integer
read as a 0-based index on one side, rejected on the other), so the resolver
is shared, not twinned (#2744 review).

Stdlib-only on purpose: this leaf must stay importable from any layer without
dragging package dependencies along.
"""

import re
from typing import Any, Dict, Optional

# #1629: fallacy records name their target by *identifier* — ``arg_1``,
# ``arg_2``, … — minted by ``shared_state._generate_id`` as
# ``f"{prefix}_{index + 1}"`` over an insertion-ordered dict. Resolution is that
# generation's inverse.
ARG_ID_RE = re.compile(r"^\s*arg_(\d+)\s*$")


# #1633 — the three key conventions a fallacy record may name its target by.
# Ordered most-specific first. An explicit loop rather than a chained ``get``
# default: producers emit the key with a ``None`` value when a detection has no
# target, and ``get(k, default)`` returns that ``None`` instead of the default.
FALLACY_TARGET_KEYS = ("target_argument", "target_argument_id", "target_arg_id")


def read_fallacy_target(fallacy: Dict[str, Any]) -> Any:
    """First non-empty target reference a fallacy record carries, or ``None``."""
    for key in FALLACY_TARGET_KEYS:
        value = fallacy.get(key)
        if value:
            return value
    return None


def resolve_target_argument_index(raw_target: Any, count: int) -> Optional[int]:
    """Resolve an upstream ``arg_N`` reference to a 0-based index below ``count``.

    ``arg_1``, ``arg_2``, … are minted by ``shared_state._generate_id`` as
    ``f"{prefix}_{index + 1}"`` over an insertion-ordered dict, and by
    ``_extract_arguments_for_parallel`` as ``f"arg_{i+1}"`` over the extract
    phase's argument list — the same 1-based enumeration in both cases, so the
    inverse is arithmetic, not matching.

    Returns ``None`` when the reference is absent, malformed (e.g. the
    ``paragraph_N`` ids the heuristic fallback mints, or a bare integer no
    producer of these keys writes), or out of range. The caller must NOT guess
    in that case (#1019).
    """
    if not raw_target:
        return None
    match = ARG_ID_RE.match(str(raw_target))
    if not match:
        return None
    index = int(match.group(1)) - 1  # IDs are 1-based
    return index if 0 <= index < count else None
