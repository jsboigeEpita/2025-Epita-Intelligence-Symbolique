r"""Deterministic post-render vocabulary check of the reader surface (#1914, c. 1+7).

Third consumer of the rendered body, beside
:func:`~.factual_consistency_check.check_factual_consistency` (formal-verdict
theatre) and :func:`~.surplus_grounding_check.check_surplus_grounding`
(ungrounded surplus claims). This one holds the two criteria of the issue
that share one shape — a vocabulary that must LEAVE the reader surface
while SURVIVING in the folded appendix (criterion 6 requires exactly that
survival):

* **criterion 1** — reader-facing acts carry no issue numbers, internal
  spec references, raw Python/JSON dictionaries or gate self-diagnostics;
* **criterion 7** — raw specialist badges cannot leak into the acts while
  remaining present in the appendix.

## The measured map this builds on (see the issue, dispatch R1030)

One family parameterized by token classes, NOT one instrument per
criterion. Each class below is a DISCOVERED gap — the occupied ground
stays where it is: the readability gate keeps its machinery family
(``acceptés [`` brackets, ``extension X :`` enumerations, ``word(s)``
morphology, ``→``, dotted taxonomy codes, scored bare refs), the eight
producer guards keep guarding the prompt, and the folded gate block is
already held by ``test_reader_surface_gate_block_1914``.

The check scans the **body only** — the assembled acts, never the folded
appendix. That boundary IS the ± pair's appendix half: the same tokens
that FAIL on the reader surface are contractual material inside the fold
(specialist inventories, counters, taxonomy IDs, protocol details — the
issue's Appendix section). A detector widened to bite the appendix would
have turned the contract around.

## Token classes

* ``#\d{3,4}`` issue numbers — unambiguous, FAIL at first hit;
* ``spec §`` / ``§\d`` internal spec pointers — unambiguous, FAIL;
* serialized dict literals ``{"key": …}`` — unambiguous in French prose,
  FAIL;
* gate self-diagnostic echoes (« gate lisibilité », « non truqué »,
  « contrôles structurels », self-check) — the block is folded; an echo
  in an act is the LLM reciting the machinery, FAIL;
* score-less specialist badges (« Verdict FOL : théorie inconsistante »,
  « PL : 3 inférences inconsistantes ») — the line-lead axis token + colon
  shape. WARN at 1–2 (residual), FAIL at ≥3 (manifest enumeration) — same
  banding as the gate's bare-ref and taxonomy-code families. A WOVEN
  sentence (« le solveur Tweety confirme… ») does not match: the shape,
  not the framework mention, is the defect (the #2046 scope guard).
"""

from __future__ import annotations

import re
from typing import List

from .fr_accord import accord
from .readability_gate import GateVerdict

# --- the token classes ---------------------------------------------------------

# #NNNN issue numbers. The lookbehind keeps identifiers (``arg_#1``) and the
# heading fence (``###`` followed by a space) out; 3-4 digits matches this
# repo's issue range without matching colours (#FFF) or short refs (#12).
_ISSUE_NUMBER_RE = re.compile(r"(?<![0-9A-Za-z_])#\d{3,4}\b")

# Internal spec pointers, both spellings the fixed surfaces carried.
_SPEC_REF_RE = re.compile(r"\bspec\s*§|§\s*\d")

# A serialized dict opening: quoted key + colon. Nothing legitimate in
# French narrative prose matches this shape.
_DICT_LITERAL_RE = re.compile(r"\{\s*[\"'][\w.\- ]+[\"']\s*:")

# Gate self-diagnostic vocabulary. The verdict block itself is folded
# (#2086); these tokens surviving in an ACT are the LLM echoing the
# machinery it was told stays behind the curtain.
_GATE_ECHO_TOKENS = (
    "gate lisibilité",
    "non truqué",
    "contrôles structurels",
    "self-check",
    "autocontr",
)

# A raw specialist badge: the line LEADS with the axis/solver token
# (optionally after a list bullet or the word « verdict »), then a colon.
# « Verdict FOL : théorie inconsistante » — the exact shape the R1029
# probe measured invisible to the scored bare-ref detector, at any dose.
# A woven sentence never matches: the axis has to lead the line for this
# to be an enumeration entry, not prose.
_BARE_BADGE_RE = re.compile(
    r"^\s*(?:[-*•]\s*)?(?:verdict\s+)?(?:pl|fol|modal|modale|tweety|dung|aspic)\s*[:：]\s*\S",
    re.IGNORECASE | re.MULTILINE,
)

_BADGE_WARN_THRESHOLD = 2  # 1–2 residual badges → WARN (gate-family precedent)
_BADGE_FAIL_THRESHOLD = 3  # ≥3 → FAIL (manifest enumeration)


def _lines(body: str) -> List[str]:
    return [line for line in body.splitlines() if line.strip()]


def check_reader_vocabulary(body: str) -> GateVerdict:
    """Deterministic post-render check of the reader-surface vocabulary.

    Args:
        body: the rendered narrative body (the 3 acts, excluding the folded
            appendix) — the surface the criteria govern. The appendix is
            deliberately out of scope: its carrying these tokens is the
            contract (criterion 6), not a violation.

    Returns:
        A :class:`~.readability_gate.GateVerdict` — ``FAIL`` when an
        unambiguous internal token (issue number, spec pointer, dict
        literal, gate echo) reaches the reader surface, or when bare
        specialist badges enumerate (≥3); ``WARN`` for 1–2 residual
        badges; ``PASS`` on a clean surface. Reasons are per-class,
        counted, with a first-hit preview — auditable, mergeable.
    """
    reasons: List[str] = []
    worst = "PASS"

    issue_hits = list(_ISSUE_NUMBER_RE.finditer(body))
    if issue_hits:
        worst = "FAIL"
        reasons.append(
            f"Vocabulaire interne (#1914, c.1) — "
            f"{accord(len(issue_hits), 'numéro d', 'numéros d')}"
            f"'issue sur la surface lecteur (ex : "
            f"{issue_hits[0].group(0)}). Les références "
            f"d'issue n'appartiennent pas au récit."
        )

    spec_hits = list(_SPEC_REF_RE.finditer(body))
    if spec_hits:
        worst = "FAIL"
        reasons.append(
            f"Vocabulaire interne (#1914, c.1) — "
            f"{accord(len(spec_hits), 'référence de spec interne', 'références de spec internes')} "
            f"sur la surface lecteur (ex : "
            f"{spec_hits[0].group(0)}). Le récit cite ses "
            f"preuves, pas la spécification qui l'a produit."
        )

    dict_hits = list(_DICT_LITERAL_RE.finditer(body))
    if dict_hits:
        worst = "FAIL"
        reasons.append(
            f"Vocabulaire interne (#1914, c.1) — "
            f"{accord(len(dict_hits), 'dictionnaire brut sérialisé', 'dictionnaires bruts sérialisés')} "
            f"dans le récit (ex : « "
            f"{dict_hits[0].group(0)}… »). Les données "
            f"appartiennent à l'annexe repliée."
        )

    gate_echoes = [
        line.strip()
        for line in _lines(body)
        if any(token in line.lower() for token in _GATE_ECHO_TOKENS)
    ]
    if gate_echoes:
        worst = "FAIL"
        reasons.append(
            f"Vocabulaire interne (#1914, c.1) — "
            f"{accord(len(gate_echoes), 'écho du diagnostic de gate', 'échos du diagnostic de gate')} "
            f"dans le récit (ex : « {gate_echoes[0][:100]} »). Le gate "
            f"parle dans le pli, jamais dans l'acte."
        )

    badges = [line.strip() for line in _lines(body) if _BARE_BADGE_RE.match(line)]
    if len(badges) >= _BADGE_FAIL_THRESHOLD:
        worst = "FAIL"
    elif badges and worst == "PASS":
        worst = "WARN"
    if badges:
        reasons.append(
            f"Badge de spécialiste brut (#1914, c.7) — "
            f"{accord(len(badges), 'ligne mène par le nom d', 'lignes mènent par le nom d')}"
            f"'axe puis deux-points (ex : « {badges[0][:100]} »). Le "
            f"verdict formel se tisse dans la prose, il ne s'énumère pas ; "
            f"l'inventaire exhaustif vit en annexe."
        )

    if not reasons:
        return GateVerdict(band="PASS")
    return GateVerdict(band=worst, reasons=reasons)
