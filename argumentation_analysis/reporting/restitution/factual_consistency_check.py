"""Deterministic post-render factual cross-check of prose vs appendix (#1316).

Complements the *structural* readability gate (``readability_gate.py``, which
enforces the weaving rule of spec §4) with a *factual* check: does the rendered
narrative cite a formal framework as the authority for a verdict the formal data
does not actually support?

## The gap this closes

The honesty guarantee of the restitution report rests on two pillars:

1. **Prompt discipline** — ``#1297`` removed the Tweety-priming phrasing from the
   Acte II ``CONSIGNE`` and added an ``INTERDIT`` guardrail, pinned by the
   regression test ``TestTweetyInconsistanceGapRegression``.
2. **The LLM obeying that guardrail** — untested, because LLM output is
   non-deterministic by nature.

The regression test asserts on the *prompt contract* (deterministic) only; it
cannot see the rendered prose. The structural readability gate checks presence
and weaving — it deliberately treats « le solveur Tweety confirme
l'inconsistance » as *woven* (the verb ``confirme`` anchors it), so it passes a
sentence whose factual claim contradicts the appendix.

Empirically (R485 artifacts, base ``976aea28``), all 3 restitutions **PASSED**
the readability gate despite Acte II claiming *« le solveur Tweety confirme
l'inconsistance »* on every corpus while the appendix reported
``inconsistantes: 0`` everywhere — the contradiction ``#1297`` later fixed at
the prompt level. **This module is the post-render detector for the residual
class of bug** (*prose theatre*): prose invoking a formal authority in a
direction the formal data does not support.

## Approach (#1316 option A — narrow, deterministic, defense-in-depth)

After render, scan the Acte II narrative body: if a line cites a **formal
authority** (Tweety, Dung, ASPIC, SPASS, EProver, PySAT, … or the generic
« solveur »/« solver ») **and** asserts an inconsistency
(``inconsist*`` / ``insatisfais*``), then the appendix's formal-axis aggregates
must actually support an inconsistency (``inconsistantes > 0``,
``insatisfiables > 0``, or a decided ``consistante: False``). If none does, the
claim is unsupported → the report is flagged **FAIL** with an auditable reason.

The check is heuristic and cheap. It never needs LLM determinism and survives
model swaps. It composes with the ``#1297`` prompt guardrail as defense in
depth: the prompt *inhibits* the theatre, this module *detects* any that leaks
through. Symmetric guards (Dung, score-qualité conflation) are possible but out
of scope here — this targets the empirical failure mode (#1276 / po-2023 R487).

Honesty contract (#1019): the check only ever *reports*; when the appendix data
is absent (``state is None``) or no authority-backed inconsistency claim is
present, it returns ``PASS`` silently rather than manufacturing a verdict.
"""

from __future__ import annotations

import re
from typing import Any, List, Mapping, Optional

from .appendix import _provenance_counts
from .readability_gate import GateVerdict

# Formal frameworks / external solvers that, when cited in the narrative, turn a
# bare "inconsistance" mention into an authority-backed formal claim. Mirrors the
# spirit of readability_gate._FRAMEWORK_SOLVERS but keeps to the formal-inference
# authorities (FOL/PL/modal), plus the generic "solveur"/"solver" wording the
# report prose actually uses (« le solveur Tweety … »).
_FORMAL_AUTHORITIES = (
    "tweety",
    "tweetyproject",
    "dung",
    "aspic",
    "spass",
    "eprover",
    "e prover",
    "pysat",
    "mace4",
    "prover9",
    "solveur",  # generic FR — « le solveur X confirme l'inconsistance »
    "solver",  # generic EN
)

# A claim of formal inconsistency. Matches the report's own vocabulary
# (« inconsistantes », « insatisfaisables »). Intentionally excludes the generic
# « invalide » (too noisy — used for informal invalidation too) to keep the
# detector narrow to the *formal-inconsistency* theatre class.
_INCONSISTENCE_RE = re.compile(r"inconsist|insatisfais", re.IGNORECASE)


def _axis_supports_inconsistance(axis: Any) -> bool:
    """Does a formal-axis status (from ``_provenance_counts``) record a decided
    inconsistency?

    Covers every axis shape :func:`appendix._fol_axis_status` /
    :func:`_pl_axis_status` / :func:`_modal_axis_status` emit:

    * FOL / modal-list: ``{"inconsistantes": n, …}``
    * PL: ``{"insatisfiables": n, …}``
    * modal-mapping: ``{"consistante": False}``

    A *degraded* axis (``None`` verdict) never counts — it is unverified, not
    inconsistent (#1019: ``None`` is never collapsed to a decided ``False``).
    A string status ("indisponible", "disponible") means the axis did not decide
    an inconsistency, so it does not support an inconsistency claim.
    """
    if isinstance(axis, Mapping):
        if axis.get("inconsistantes"):
            return True
        if axis.get("insatisfiables"):
            return True
        if axis.get("consistante") is False:
            return True
    return False


def _axes_support_inconsistance(state: Mapping[str, Any]) -> bool:
    """Does ANY formal axis in the appendix support a decided inconsistency?"""
    counts = _provenance_counts(state)
    return any(
        _axis_supports_inconsistance(counts.get(k))
        for k in ("axe_fol", "axe_pl", "axe_modale")
    )


def _unsupported_authority_claims(body: str, *, supported: bool) -> List[str]:
    """Authority-backed inconsistency claims in ``body`` that the data refutes.

    When ``supported`` is True (the appendix records a decided inconsistency
    somewhere), authority-backed inconsistency claims are legitimate and an empty
    list is returned — no theatre. When ``supported`` is False, every line that
    cites a formal authority AND asserts an inconsistency is unsupported theatre
    and is returned (stripped) for an auditable reason.
    """
    if supported:
        return []
    claims: List[str] = []
    for line in body.splitlines():
        low = line.lower()
        if not _INCONSISTENCE_RE.search(low):
            continue
        if any(auth in low for auth in _FORMAL_AUTHORITIES):
            stripped = line.strip()
            if stripped and stripped not in claims:
                claims.append(stripped)
    return claims


def check_factual_consistency(
    body: str,
    state: Optional[Mapping[str, Any]],
) -> GateVerdict:
    """Deterministic post-render cross-check of prose vs appendix (#1316, opt A).

    Args:
        body: the rendered narrative body (the 3 acts concatenated, *excluding*
            the folded appendix). This is the surface where prose theatre lives.
        state: the shared-state mapping the appendix was rendered from (the
            source of truth for formal verdicts). ``None`` when the renderer was
            called without a state — in that case the check is skipped (PASS),
            honestly, rather than inventing a verdict from missing data.

    Returns:
        A :class:`~.readability_gate.GateVerdict` — ``FAIL`` with an auditable
        reason when the prose cites a formal authority for an inconsistency the
        appendix does not record (prose theatre); ``PASS`` otherwise. Mergeable
        with the structural readability verdict via ``GateVerdict.merge``.
    """
    if state is None:
        return GateVerdict(band="PASS")

    supported = _axes_support_inconsistance(state)
    claims = _unsupported_authority_claims(body, supported=supported)
    if not claims:
        return GateVerdict(band="PASS")

    preview = claims[0][:100]
    return GateVerdict(
        band="FAIL",
        reasons=[
            f"Prose theatre (#1316) — {len(claims)} affirmation(s) du récit "
            f"cite(nt) un cadre formel (Tweety/Dung/ASPIC/…) comme autorité "
            f"d'une inconsistance que l'annexe ne soutient pas (axes formels : "
            f"inconsistance décidée = {supported}). La prose contredit les "
            f"données de provenance. Ex : « {preview} »."
        ],
    )
