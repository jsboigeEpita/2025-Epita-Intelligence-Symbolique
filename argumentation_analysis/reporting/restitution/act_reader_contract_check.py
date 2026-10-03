"""Deterministic post-render checks of the reader contract on the acts
(#1914, criteria 2, 3 and 4 — dispatch R1059).

The producer side of these three criteria is held at the prompt + evidence
level (the derivation consigne, the device-function consigne, the salience
ranker — pinned by ``test_formal_derivation_channel_1914``,
``test_rhetorical_device_channel_1914`` and ``test_conclusion_salience_1914``).
The card (c.5969933470) measured the shared gap: NO test reads a rendered
act, and the coordinator's paid render of 01/10 showed the exact defect
(fallacy labels piling instead of naming what a reader recognizes).

These three controls are the mechanical half of the closure. Each is a PURE
function ``act text -> findings`` (with positions), in the family of
:func:`~.surplus_grounding_check.check_surplus_grounding` and
:func:`~.reader_vocabulary_check.check_reader_vocabulary`, with one
contractual difference (dispatch R1059): **the findings are diagnostics for
the folded appendix — the control never modifies an act and never fails a
render.** The prose is a model output: one degrades in the state, one does
not raise. There is therefore NO ``GateVerdict`` here — findings ride into
the appendix as their own audit section.

What each control reads:

* **criterion 2** — a sentence citing a formal result (solver name, axis
  badge, refutation/inconsistency verdict) must carry, in the SAME sentence,
  what was tested and what it changes. The honest absence (« contenu testé
  non disponible », « compteur seul ») is compliant: naming the missing
  derivation is the contract, not a violation.
* **criterion 3** — a sentence carrying a device/fallacy label cue without
  any function marker: the piling-labels shape the paid render measured.
* **criterion 4** — the Act III ranked shape: a ranking marker must be
  present, and label-cue mentions must not exceed the ranker's own
  structural cap (5, :func:`.conclusion_salience` — a cap taken from the
  producer, never tuned against the calibration corpus).

Calibration is a measurement, not a verdict wiring: a control firing on
~100 % or ~0 % of real renders does not discriminate, is reported as such
and is NOT wired as a verdict. Thresholds in this module are structural
(the producer's own constants) or absent (pure observation), never fitted
to make the real corpus pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

# -- finding -----------------------------------------------------------------


@dataclass(frozen=True)
class ContractFinding:
    """One reader-contract observation on a rendered act — a diagnostic for
    the appendix, never a render failure."""

    criterion: int  # 2, 3 or 4
    kind: str  # machine-readable shape, e.g. "formal_citation_without_change"
    act: str  # "Acte II" / "Acte III" (the act the sentence lives in)
    line: int  # 1-based line in the rendered body
    excerpt: str  # <= 120 chars of the offending sentence, audit-side only
    note: str  # what the finding means, in reader language


# -- act splitting -----------------------------------------------------------

_ACT_HEADING_RE = re.compile(r"^## (Acte (?:I|II|III))\b.*$", re.MULTILINE)


def _split_acts(body: str) -> List[Tuple[str, str, int]]:
    """(act label, act text, 0-based body line of the heading) triples, in
    document order. The preamble before Acte I is dropped (it is not an
    act). The heading's own line offset makes every finding's line number
    absolute in the rendered body."""
    matches = list(_ACT_HEADING_RE.finditer(body))
    acts: List[Tuple[str, str, int]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        first_line = body.count("\n", 0, start)
        acts.append((m.group(1), body[start:end], first_line))
    return acts


# -- sentences ---------------------------------------------------------------

# A French sentence ends at . ! ? … (a colon introduces the elaboration of
# the SAME sentence — « ... : ce que ça change » is one sentence).
_SENTENCE_END_RE = re.compile(r"[.!?…]")

# French LLM prose writes the typographic apostrophe (U+2019); markers store
# the straight one — normalise before matching (#2032 lesson).
_APOSTROPHE = ("’", "'")


def _sentences_with_lines(act_text: str, act_offset: int) -> List[Tuple[str, int]]:
    """(sentence, 1-based body line of its first char) for every sentence in
    the act. ``act_offset`` is the 0-based line of the act's first line."""
    out: List[Tuple[str, int]] = []
    for rel_line, raw in enumerate(act_text.splitlines()):
        line = raw.replace(*_APOSTROPHE)
        pos = 0
        for part in _SENTENCE_END_RE.split(line):
            stripped = part.strip()
            if stripped:
                out.append((stripped, act_offset + rel_line + 1))
            pos += len(part) + 1
    return out


def _excerpt(sentence: str) -> str:
    return sentence if len(sentence) <= 120 else sentence[:117] + "…"


# -- criterion 2: formal citation without derivation --------------------------

# A sentence CITES a formal result through a solver name, an axis badge or a
# formal verdict word. The bracket forms are the raw badge shapes the real
# renders carry (« [pl] 3 inférence(s) PL consistantes — ancrage : solveur
# Tweety »).
_FORMAL_CITATION_RE = re.compile(
    r"\[\s*(?:pl|fol|modal)\s*\]|\bsolveurs?\b|tweety|spass|\bdung\b|aspic"
    r"|\br[ée]fut(?:ée?|ion)\b|inconsistante?\b|\br[ée]fut[ée]es?\b",
    re.IGNORECASE,
)

# The derivation halves. « inférence » is deliberately NOT a tested marker:
# it is the badge's own counting word (« 3 inférence(s) PL consistantes »
# names a count, not a tested proposition).
_TESTED_RE = re.compile(
    r"test[ée]|\b[àa] l'[ée]preuve\b|proposition|clause|pr[ée]dicat|atome|formule",
    re.IGNORECASE,
)
_CHANGE_RE = re.compile(
    r"chang|fragilis|remet en cause|oblige|reconsid|[ée]pend\b|montre|r[ée]v[èe]le"
    r"|signifi|impliqu|entra[îi]n|renfor[çc]|condamn|[ée]tablit|juge",
    re.IGNORECASE,
)

# The honest-absence wording the Act II evidence itself carries for a
# placeholder-only record — naming the missing derivation is compliant.
_HONTEST_ABSENCE_RE = re.compile(r"non disponible|compteur seul", re.IGNORECASE)


def _formal_findings(acts: List[Tuple[str, str, int]]) -> List[ContractFinding]:
    findings: List[ContractFinding] = []
    for label, text, first_line in acts:
        if label == "Acte I":
            continue  # situation act: no formal citation is expected there
        for sentence, line in _sentences_with_lines(text, first_line):
            norm = sentence.lower()
            if not _FORMAL_CITATION_RE.search(norm):
                continue
            if _HONTEST_ABSENCE_RE.search(norm):
                continue
            has_tested = bool(_TESTED_RE.search(norm))
            has_change = bool(_CHANGE_RE.search(norm))
            if has_tested and has_change:
                continue
            kind = (
                "formal_citation_without_derivation"
                if not has_tested and not has_change
                else (
                    "formal_citation_without_tested"
                    if not has_tested
                    else "formal_citation_without_change"
                )
            )
            missing = (
                "ni ce qui a été testé ni ce que ça change"
                if not has_tested and not has_change
                else (
                    "ce qui a été testé"
                    if not has_tested
                    else "ce que ça change pour le jugement"
                )
            )
            findings.append(
                ContractFinding(
                    criterion=2,
                    kind=kind,
                    act=label,
                    line=line,
                    excerpt=_excerpt(sentence),
                    note=f"citation formelle sans {missing} dans la même phrase "
                    f"(critère 2 — le lecteur reçoit un badge, pas une dérivation)",
                )
            )
    return findings


# -- criterion 3: label without function --------------------------------------

# A sentence carries a LABEL cue (the defect taxonomy vocabulary) or piles
# quoted labels; a FUNCTION marker is what the device accomplishes (« visant
# à… », « pour légitimer… » — the justification's own clause shapes, #2060).
_LABEL_CUE_RE = re.compile(
    r"sophisme|proc[ée]d[ée]|figure de style|fallacie|paralogisme",
    re.IGNORECASE,
)
_FUNCTION_RE = re.compile(
    r"accomplit|visant|vise [àa]|cherche [àa]|afin de|en vue de|de sorte [àa]"
    r"|l[ée]gitim|cr[ée]e|cr[ée]dibilis|installe|instaur|permet de|rassure"
    r"|s[ée]duit|endoctrin|d[ée]responsabilis|fonction",
    re.IGNORECASE,
)
# Label piling: >= 2 short quoted segments in one sentence (the paid render's
# measured shape — « généralités flatteuses », « ingratiation »… stacked).
_QUOTED_SEGMENT_RE = re.compile(r"«\s*([^»]{2,60})\s*»")


def _label_findings(acts: List[Tuple[str, str, int]]) -> List[ContractFinding]:
    findings: List[ContractFinding] = []
    for label, text, first_line in acts:
        if label == "Acte I":
            continue
        for sentence, line in _sentences_with_lines(text, first_line):
            norm = sentence.lower()
            cue = _LABEL_CUE_RE.search(norm)
            quoted = _QUOTED_SEGMENT_RE.findall(sentence)
            if not cue and len(quoted) < 2:
                continue
            if _FUNCTION_RE.search(norm):
                continue
            kind = "label_without_function"
            findings.append(
                ContractFinding(
                    criterion=3,
                    kind=kind,
                    act=label,
                    line=line,
                    excerpt=_excerpt(sentence),
                    note="étiquette de procédé/sophisme sans ce qu'il accomplit "
                    "dans la même phrase (critère 3 — une étiquette ne dit pas "
                    "ce qu'un lecteur reconnaît)",
                )
            )
    return findings


# -- criterion 4: Act III ranked shape ----------------------------------------

# A ranking marker: the producer's own hierarchy vocabulary (P1/P2/P3 from
# conclusion_salience) or its reader-language equivalents.
_RANKED_MARKER_RE = re.compile(
    r"\bP[123]\b|d[ée]cisif|d[ée]terminant|priorit|hi[ée]rarch|l'essentiel"
    r"|en premier|par ordre d'importance",
    re.IGNORECASE,
)

# The label-replay ceiling is the ranker's own structural cap — never tuned
# against the calibration corpus (dispatch R1059, anti-pendulum).
_RANKED_CAP = 5


def _ranked_findings(acts: List[Tuple[str, str, int]]) -> List[ContractFinding]:
    act3 = next(((l, t, o) for l, t, o in acts if l == "Acte III"), None)
    if act3 is None:
        return []  # honest skip: no Act III to judge (missing act is the
        # renderer's own loud degradation, not this check's business)
    label, text, first_line = act3
    findings: List[ContractFinding] = []
    sentences = _sentences_with_lines(text, first_line)
    if not any(_RANKED_MARKER_RE.search(s.lower()) for s, _ in sentences):
        findings.append(
            ContractFinding(
                criterion=4,
                kind="no_ranked_marker",
                act="Acte III",
                line=first_line + 1,
                excerpt="(acte entier)",
                note="aucun marqueur de hiérarchie courte dans l'Acte III "
                "(critère 4 — la priorisation doit se voir, pas se deviner)",
            )
        )
    label_sentences = sum(
        1
        for s, _ in sentences
        if _LABEL_CUE_RE.search(s.lower()) or len(_QUOTED_SEGMENT_RE.findall(s)) >= 2
    )
    if label_sentences > _RANKED_CAP:
        findings.append(
            ContractFinding(
                criterion=4,
                kind="label_replay",
                act="Acte III",
                line=first_line + 1,
                excerpt=f"{label_sentences} phrases à étiquette dans l'Acte III",
                note=f"{label_sentences} phrases portent une étiquette — au-delà "
                f"de la limite structurelle du classement ({_RANKED_CAP}, le cap "
                "du rangeur) : rejeu d'inventaire plutôt que hiérarchie "
                "(critère 4)",
            )
        )
    return findings


# -- runner -------------------------------------------------------------------


def check_act_reader_contract(body: str) -> List[ContractFinding]:
    """Run the three criteria-2/3/4 controls on a rendered body.

    Args:
        body: the rendered narrative body (the 3 acts with their ``## Acte``
            headings — the renderer's ``body`` BEFORE the folded appendix).

    Returns:
        Findings, each with its criterion, act, line and a short excerpt —
        diagnostics for the folded appendix. NEVER a verdict: this function
        observes, it does not judge the render (dispatch R1059).
    """
    # A full document (acts + folded appendix) may be handed in — the fold
    # and everything after it are appendix material, never act prose. The
    # renderer's own body carries no fold; this cut is defensive for callers
    # passing whole documents (the calibration producer does).
    acts = _split_acts(body.split("<details>")[0])
    if not acts:
        return []
    return _formal_findings(acts) + _label_findings(acts) + _ranked_findings(acts)
