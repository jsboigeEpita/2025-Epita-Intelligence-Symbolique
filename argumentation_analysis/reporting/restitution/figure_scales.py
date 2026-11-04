"""A figure reaches the reader with its scale, its direction or its count (#3394).

Cycle 0's renders handed the non-specialist reader bare numbers — « score
producteur 0.56 », « évaluation globale 1,28 » — verdict counts without their
bar (« 7/8 arguments évalués » never said 8 of what, nor which threshold
applied), and vote support as a word with no count behind it (« une large
majorité des méthodes de vote »). A number without its scale is not
information; it is decoration the reader cannot use.

These formatters are the producers' side of #3394. The writers receive the
FORMATTED string, never the bare number — and no vocabulary rule is added to
any prompt: the figure arrives already carrying what makes it usable
(anti-pendulum, the issue's own rule).

Anti-#1019: every formatter renders an honest absence (``""``) rather than a
guess — an unmeasured or unreadable input prints nothing, and no value is
clamped or rounded into a scale it did not come from.
"""

from __future__ import annotations

from typing import Optional


def _fr_number(value: float, decimals: int) -> str:
    """The number as the renders spell it: French decimal comma."""
    return f"{value:.{decimals}f}".replace(".", ",")


def score_with_scale(
    value: Optional[float],
    maximum: Optional[float],
    *,
    higher_is_better: bool = True,
    decimals: int = 2,
    direction: Optional[str] = None,
) -> str:
    """A score with its scale and direction, e.g. « 0,56 sur 1 — plus haut = meilleur ».

    ``maximum`` is the scale's ceiling as the producer measured it — never a
    guess: a value above it is printed as it is (the defect is upstream, and
    clamping here would mask it). ``None`` or a non-finite input prints
    nothing (honest absence). ``direction`` overrides the computed label for
    scales whose good side is neither « meilleur » nor « pire » — severity
    says « plus haut = plus grave ».
    """
    if value is None or maximum is None:
        return ""
    try:
        v = float(value)
        m = float(maximum)
    except (TypeError, ValueError):
        return ""
    if v != v or m != m:  # NaN — math.isnan without the import
        return ""
    if direction is None:
        direction = (
            "plus haut = meilleur" if higher_is_better else "plus bas = meilleur"
        )
    return f"{_fr_number(v, decimals)} sur {_fr_number(m, decimals)} — {direction}"


def sum_on_its_maximum(value: Optional[float], n_terms: Optional[int]) -> str:
    """A sum with the number of terms it ran over: « 1,28 sur 5 ».

    A quality ``overall`` is a SUM of per-virtue [0, 1] scores whose ceiling
    varies by unit (#1942 — post-#1923 the tri-state machinery leaves
    inapplicable virtues absent, so the denominator is the count of
    EVALUATED virtues). That count is the score's own scale, and the #3394
    example shape prints the value with it: « 1,28 sur 5 ». ``None``, a
    non-finite value or a missing/zero term count prints nothing — a sum
    whose ceiling is unmeasurable is the bare-number defect again
    (anti-#1019).
    """
    if value is None or not n_terms or n_terms <= 0:
        return ""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    if v != v:  # NaN
        return ""
    return f"{_fr_number(v, 2)} sur {n_terms}"


def vote_count_phrase(
    support: Optional[int], n_methods: Optional[int]
) -> Optional[str]:
    """A vote's support as the counted fact: « 9 des 12 méthodes ».

    The count comes from governance's own record — the number of deciding
    methods that elected the rendered winner, over the number that decided.
    ``None`` when either side of the fraction is missing or zero: a count
    without its population is the bare-number defect again (anti-#1019).
    """
    if not support or not n_methods or n_methods <= 0 or support <= 0:
        return None
    return f"{support} des {n_methods} méthodes"


def penalised_sum_on_its_maximum(
    value_after: Optional[float],
    value_before: Optional[float],
    n_terms: Optional[int],
) -> str:
    """A penalised sum on its own ceiling, saying the penalty: « 4,25 sur 6
    après pénalité (6,00 avant) ».

    #3394 follow-up (R1142): on the cycle-0 states 38 of 67 quality entries
    are ``original_score × (1 − penalty_factor)`` while the ranking's base
    clause called every figure a plain sum — the same class as ask 5, on the
    render's side. The adjusted sum rides its own ceiling; the pre-penalty
    sum rides beside it so the reader sees WHICH figure the penalty moved.
    Falls back to the marker without the parenthetical when the record
    carries no readable ``original_score`` — the penalty is a fact of the
    record (``applied``), only the before-VALUE needs a number.
    """
    base = sum_on_its_maximum(value_after, n_terms)
    if not base:
        return ""
    try:
        before = float(value_before)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return f"{base} après pénalité"
    if before != before:  # NaN
        return f"{base} après pénalité"
    return f"{base} après pénalité ({_fr_number(before, 2)} avant)"
