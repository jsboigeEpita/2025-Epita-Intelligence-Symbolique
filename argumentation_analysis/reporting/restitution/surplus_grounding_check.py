"""Deterministic post-render grounding of the surplus claim (#1914, criterion 8).

Complements :func:`~.factual_consistency_check.check_factual_consistency`
(another consumer of the rendered body + shared-state pair) with the
reader-chair acceptance criterion the issue exists to enforce:

    *A reader-chair fixture rejects a report whose only multi-agent surplus
    is counters/labels without a changed interpretive conclusion.*

## The gap this closes (measured by the coordinator, R1029)

The producer side is honest — when the deterministic split
(:func:`.conclusion_salience.assess_conclusion_salience`) finds nothing a
strong zero-shot reading could not produce, the Acte III prompt carries the
explicit refusal (« RIEN au-delà d'une lecture attentive … NE SONT PAS un
surplus interprétatif », pinned by ``TestReaderChair``). But nothing checked
the **rendered** text: a probe report whose Acte III claims « un surplus
interprétatif décisif … la conclusion interprétative s'en trouve modifiée »
on exactly such a state rendered ``band=PASS``, ``passed=True``, zero
remarks. A contract guarded at the prompt level is a contract on what was
asked, not on what was written — same class as the #1316 prose theatre this
package already detects.

## Approach

After render, re-derive the surplus from the shared-state mapping — the
same single reader chain the Acte III prompt itself used
(``build_act3_evidence`` → ``evidence.salience.surplus``), never trusting
what the act claims. Then:

* ``established`` non-empty → the report's surplus claims are grounded:
  **PASS unconditionally** — no lexical scan at all. This is the
  anti-pendulum half of the contract: the fixture rejects the *unsupported
  claim*, never the mention of multi-agent work. A detector that banned the
  surplus vocabulary would mute Acte III exactly where it has something
  true to say.
* ``established`` empty → scan the narrative body for an *affirmative*
  surplus claim (the surplus notion, a beyond-a-plain-reading statement, or
  a changed-conclusion claim) not carried by a negation guard. Each hit is
  unsupported theatre: counters and labels are procedural matter, and the
  report may inventory them but must not sell them as interpretive surplus.

Honesty contract (#1019): ``state is None`` (no source of truth) or a state
the salience reader cannot process skips the check (PASS), named rather
than conflated with a measured-empty surplus.
"""

from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any, List, Mapping, Optional

from .fr_accord import accord
from .readability_gate import GateVerdict

# A line claims interpretive surplus when it invokes the surplus notion
# itself (« surplus interprétatif »), or states something beyond a plain
# reading (« au-delà d'une lecture attentive »), or asserts the analysis
# changed the interpretive conclusion. Each cue is the affirmative form the
# probe report measured; the honest-refusal wording is excluded by the
# negation guards below, not by narrowing these cues.
_SURPLUS_NOTION_RE = re.compile(r"surplus.*interpr[ée]tatif|interpr[ée]tatif.*surplus")
_BEYOND_READING_RE = re.compile(r"au[- ]del[àa]\s+d'une?\s+(\w+\s+){0,2}lecture")
_CHANGED_CONCLUSION_RE = re.compile(
    r"(conclusion|interpr[ée]tation|interpr[ée]tative).{0,60}"
    r"(modifi|chang|transform|alt[ée]r|boulevers|d[ée]cisif)",
    re.DOTALL,
)

# The honest-refusal half of the contract: a line that negates the surplus
# (the canonical wording the Acte III data block carries when nothing was
# established) is not a claim. Line-scoped, like the cues. Stored accented
# and apostrophe-straight: the scanned line is lowercased and apostrophe-
# normalised only — its accents survive, so must the guards'.
_NEGATION_GUARDS = (
    "rien",
    "aucun",
    "aucune",
    "n'est pas",
    "ne sont pas",
    "n'a pas",
    "n'établit",
    "n'a établi",
    "pas un surplus",
    "pas de surplus",
    "sans surplus",
    "ne change",
    "pas changé",
    "inchange",
    "sans changer",
    "sans modifier",
)

# French LLM prose writes the typographic apostrophe (U+2019); the guards
# store the straight one (U+0027) — normalise before matching (#2032 lesson).
_APOSTROPHE_NORMALISED = ("’", "'")


def _rederived_established_is_empty(state: Mapping[str, Any]) -> bool:
    """Re-derive the surplus split from the appendix mapping — False when the
    check cannot run (no derivable salience: honest skip, not a measured
    empty). Same single reader chain as the Acte III prompt: the mapping is
    adapted back to attribute access (mechanically — every key it carries
    becomes an attribute), then ``build_act3_evidence`` derives the bundle.
    """
    # Lazy import: the plugin imports conclusion_salience, and heavy plugin
    # deps must not become renderer-module-load cost (same pattern as
    # conclusion_salience.projection_from_state).
    from .act3_conclusion_plugin import build_act3_evidence

    shim = SimpleNamespace(**dict(state))
    evidence = build_act3_evidence(shim)
    if evidence.salience is None:
        return False
    return not evidence.salience.surplus.established


def _unsupported_surplus_claims(body: str) -> List[str]:
    """Affirmative surplus claims in ``body`` (stripped lines, deduplicated).

    A line is a claim when any cue matches; a line carrying a negation
    guard never is, whatever else it says — the honest refusal and the
    scoped inventory (« sept sophismes localisés », without the surplus
    notion) both pass untouched.
    """
    claims: List[str] = []
    for raw_line in body.splitlines():
        line = raw_line.lower().replace(*_APOSTROPHE_NORMALISED)
        if any(guard in line for guard in _NEGATION_GUARDS):
            continue
        hit = (
            _SURPLUS_NOTION_RE.search(line)
            or _BEYOND_READING_RE.search(line)
            or _CHANGED_CONCLUSION_RE.search(line)
        )
        if not hit:
            continue
        stripped = raw_line.strip()
        if stripped and stripped not in claims:
            claims.append(stripped)
    return claims


def check_surplus_grounding(
    body: str,
    state: Optional[Mapping[str, Any]],
) -> GateVerdict:
    """Deterministic post-render grounding of the surplus claim (#1914, c. 8).

    Args:
        body: the rendered narrative body (the 3 acts concatenated, excluding
            the folded appendix) — the surface where the surplus claim lives.
        state: the shared-state mapping the appendix was rendered from (the
            source of truth the surplus is re-derived from). ``None`` when
            the renderer was called without a state — the check is skipped
            (PASS), honestly, rather than judging from missing data.

    Returns:
        A :class:`~.readability_gate.GateVerdict` — ``FAIL`` with an
        auditable reason when the prose claims an interpretive surplus the
        re-derived state does not support (counters/labels theatre);
        ``PASS`` otherwise, including whenever the state establishes a real
        surplus (grounded claims are never lexically policed). Mergeable
        with the other verdicts via ``GateVerdict.merge``.
    """
    if state is None:
        return GateVerdict(band="PASS")
    if not _rederived_established_is_empty(state):
        return GateVerdict(band="PASS")

    claims = _unsupported_surplus_claims(body)
    if not claims:
        return GateVerdict(band="PASS")

    preview = claims[0][:100]
    return GateVerdict(
        band="FAIL",
        reasons=[
            f"Surplus non étayé (#1914, critère 8) — "
            f"{accord(len(claims), 'ligne du récit revendique', 'lignes du récit revendiquent')} "
            f"un apport interprétatif multi-agents alors que la re-dérivation "
            f"déterministe de l'état établit un surplus VIDE (aucun rôle "
            f"décisif, aucune relation structurelle, aucune convergence "
            f"non-LLM). Les compteurs et labels sont de la matière "
            f"procédurale, pas un surplus. Ex : « {preview} »."
        ],
    )
