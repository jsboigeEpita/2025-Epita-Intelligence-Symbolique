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

## The mirror direction (#1914 criterion 5, post-render half)

Criterion 8's control above polices ONE side of the claim/state relation, by
construction: an act **selling** a surplus the state does not establish. The
other side went unread — measured 2026-09-29 on ``main``: the very refusal
wording the prompt carries when the surplus is empty
(:data:`.act3_conclusion_plugin`'s « RIEN au-delà d'une lecture attentive …
NE SONT PAS un surplus interprétatif ») written on a state whose re-derived
surplus **is** established rendered ``band=PASS``, zero remarks — the reader
is told nothing was established while the analysis established something.
That is the same defect class the criterion-8 probe measured (prose
contradicting the re-derived state), in the opposite direction, and it is the
second half of criterion 5's gesture (the first half re-anchored the vacuous
prompt assertions, #2879). Same instrument, same surface, same re-derivation:
the gap was the un-policed side, not a missing consumer.

## Approach

After render, re-derive the surplus from the shared-state mapping — the
same single reader chain the Acte III prompt itself used
(``build_act3_evidence`` → ``evidence.salience.surplus``), never trusting
what the act claims. The relation is then policed in both directions:

* ``established`` empty → scan the narrative body for an *affirmative*
  surplus claim (the surplus notion, a beyond-a-plain-reading statement, or
  a changed-conclusion claim) not carried by a negation guard. Each hit is
  unsupported theatre: counters and labels are procedural matter, and the
  report may inventory them but must not sell them as interpretive surplus.
* ``established`` non-empty → the surplus *claims* are grounded and are not
  lexically policed at all. This is the anti-pendulum half of the contract:
  the fixture rejects the *unsupported claim*, never the mention of
  multi-agent work — a detector that banned the surplus vocabulary would
  mute Acte III exactly where it has something true to say. The one line
  still read is the mirror: a **denial** (a cue carried by a negation
  guard) asserts to the reader the opposite of what the state established.

Honesty contract (#1019): ``state is None`` (no source of truth) or a state
the salience reader cannot process skips the check (PASS) in both
directions, named rather than conflated with a measured-empty surplus.
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

# The SAME negation relation, second member (#2883): the ordinary verbal
# negation governing a verb — « ne conclut pas », « ne revendique pas ici »,
# « n'a jamais établi » — which the fixed vocabulary above (être/avoir
# conjugations, « rien », « sans »…) cannot see. The two members compose in
# :func:`_carries_negation`, the ONE definition both directions read —
# never a list for one direction and a regex for the other. Known,
# pre-existing imprecision, named rather than fixed here: a negation scoped
# to one object only (« pas un surplus de ce type, mais un autre ») counts
# as a denial of the whole notion — the fixed vocabulary already had that
# class, this extends it to a new surface, it does not create it.
_VERBAL_NEGATION_RE = re.compile(
    r"\b(?:ne|n['''])\s+\S+(?:\s+\S+){0,2}\s+(?:pas|plus|jamais)\b"
)

# French LLM prose writes the typographic apostrophe (U+2019); the guards
# store the straight one (U+0027) — normalise before matching (#2032 lesson).
_APOSTROPHE_NORMALISED = ("’", "'")


def _carries_negation(line: str) -> bool:
    """Does ``line`` (already lowercased and apostrophe-normalised) carry a
    negation of the surplus? ONE definition, both directions (#2883): the
    canonical refusal vocabulary, plus the verbal negation relation above.
    """
    return any(guard in line for guard in _NEGATION_GUARDS) or bool(
        _VERBAL_NEGATION_RE.search(line)
    )


def _rederived_established(state: Mapping[str, Any]) -> Optional[List[str]]:
    """The re-derived non-procedural surplus statements — ``None`` when the
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
        return None
    return [item.statement for item in evidence.salience.surplus.established]


def _claims_surplus_notion(line: str) -> bool:
    """Does ``line`` (already lowercased and apostrophe-normalised) invoke the
    surplus notion? One predicate, two directions: the affirmative claim when
    the state establishes nothing, the denial when it establishes something.
    """
    return bool(
        _SURPLUS_NOTION_RE.search(line)
        or _BEYOND_READING_RE.search(line)
        or _CHANGED_CONCLUSION_RE.search(line)
    )


def _unsupported_surplus_claims(body: str) -> List[str]:
    """Affirmative surplus claims in ``body`` (stripped lines, deduplicated).

    A line is a claim when any cue matches; a line carrying a negation
    (the one definition, :func:`_carries_negation`) never is, whatever
    else it says — the honest refusal and the scoped inventory (« sept
    sophismes localisés », without the surplus notion) both pass untouched.
    """
    claims: List[str] = []
    for raw_line in body.splitlines():
        line = raw_line.lower().replace(*_APOSTROPHE_NORMALISED)
        if _carries_negation(line):
            continue
        if not _claims_surplus_notion(line):
            continue
        stripped = raw_line.strip()
        if stripped and stripped not in claims:
            claims.append(stripped)
    return claims


def _denied_surplus_claims(body: str) -> List[str]:
    """Lines that DENY the surplus notion (stripped, deduplicated).

    The exact complement of :func:`_unsupported_surplus_claims`' predicate —
    same line scope, same cues, same negation definition
    (:func:`_carries_negation`), only the side of the guard flips. Scan this
    only when the state's re-derived surplus is established: there the denial
    asserts to the reader the opposite of what the analysis produced. The
    negation is the canonical refusal vocabulary the Acte III data block
    itself carries for the empty case (completed by the verbal relation,
    #2883), so an ordinary negated sentence about something else (« aucun
    sophisme localisé n'est resté sans réponse ») is not a denial — the cue
    must be there too.
    """
    denials: List[str] = []
    for raw_line in body.splitlines():
        line = raw_line.lower().replace(*_APOSTROPHE_NORMALISED)
        if not _carries_negation(line):
            continue
        if not _claims_surplus_notion(line):
            continue
        stripped = raw_line.strip()
        if stripped and stripped not in denials:
            denials.append(stripped)
    return denials


def check_surplus_grounding(
    body: str,
    state: Optional[Mapping[str, Any]],
) -> GateVerdict:
    """Deterministic post-render grounding of the surplus claim (#1914, c. 8
    and c. 5 mirror).

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
        re-derived state does not support (counters/labels theatre), or when
        it denies one the state does establish (the mirror, #1914 c. 5);
        ``PASS`` otherwise, including whenever the state establishes a real
        surplus and the prose does not deny it (grounded claims are never
        lexically policed). Mergeable with the other verdicts via
        ``GateVerdict.merge``.
    """
    if state is None:
        return GateVerdict(band="PASS")

    established = _rederived_established(state)
    if established is None:
        # No derivable salience: honest skip either way, never a measured
        # empty collapsed into a verdict (#1019).
        return GateVerdict(band="PASS")

    if established:
        denials = _denied_surplus_claims(body)
        if not denials:
            return GateVerdict(band="PASS")
        preview = denials[0][:100]
        return GateVerdict(
            band="FAIL",
            reasons=[
                f"Surplus démenti (#1914, critère 5) — "
                f"{accord(len(denials), 'ligne du récit déclare', 'lignes du récit déclarent')} "
                f"qu'aucun apport interprétatif n'a été établi, alors que la "
                f"re-dérivation déterministe de l'état en établit "
                f"{len(established)}. Le lecteur reçoit l'inverse de ce que "
                f"l'analyse a produit. Ex : « {preview} »."
            ],
        )

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
