"""The readability gate — mechanical enforcement of the weaving rule (spec §4).

This is the load-bearing anti-énumération contract of the restitution report.
Spec §4 states:

    For EVERY citation of a formal or informal framework (Tweety, Dung/ASPIC,
    taxonomy descent, AIF/Walton, virtues), the report MUST provide a narrative
    anchor: the framework is the *proof of a story point*, never an isolated
    list entry.

    A framework reference is valid iff it is bound to (a) a located textual move
    and (b) the concrete verdict that framework produced. A framework block with
    neither anchor is an enumeration and MUST be rejected by the readability
    gate (R6) or rewritten.

This module turns that prose rule into a deterministic, CI-friendly check. It
detects the *enumeration smell* — the spec's canonical counter-example is::

    ❌ « Sophisme : ad verecundiam (score 0.8) » — a name and a number, detached
       from any story.

The detector flags a line as a **bare framework reference** when it cites a
framework (a solver, a scheme family, or a Latin/English fallacy name) *and*
carries an isolated score *and* has no narrative verb anchoring it to a beat.
The contrast case::

    ✅ « … le solveur Tweety confirme l'inconsistance de l'inférence. »

…cites Tweety but carries a verb (``confirme``) and no isolated score, so it is
*woven*, not bare.

Honesty contract (#1019): the gate *reports* what it finds. It never
manufactures a passing verdict, and a bare reference is reported at the level
its count warrants (WARN for a residual few, FAIL for a manifest enumeration).
The verdict is surfaced in the rendered report for transparency — the gate does
not grade on a curve to please.

Optional reader-check (issue #1140): a 0-shot "non-specialist reader" LLM probe
answering three comprehension questions. Off by default; when an LLM callable is
injected it augments the structural verdict. Not run in CI (no API key).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .acts import RestitutionActs

# --- catalogues ---------------------------------------------------------------

# Formal solvers / scheme frameworks cited as *proof notes* in the narrative.
_FRAMEWORK_SOLVERS = {
    "tweety",
    "tweetyproject",
    "dung",
    "aspic",
    "aspic+",
    "aif",
    "walton",
    "jtms",
    "atms",
    "dung/aspic",
}

# Latin / English fallacy names (the "nom (latin)" the differentiator demotes).
# Lowercased substrings — matched word-boundary-light because Latin names are
# multi-word ("ad hominem"). Kept to the high-frequency families; an exhaustive
# list lives in the taxonomy and is not duplicated here (anti-pendule).
_FALLACY_NAMES = (
    "ad hominem",
    "ad verecundiam",
    "ad populum",
    "ad baculum",
    "ad misericordiam",
    "ad ignorantiam",
    "ad passum",
    "ad antiquitatem",
    "tu quoque",
    "post hoc",
    "petitio",
    "non sequitur",
    "ex falso",
    "slippery slope",
    "straw man",
    "strawman",
    "red herring",
    "redherring",
    "false dichotomy",
    "faux dilemme",
    "circular",
    "bandwagon",
    "hasty generalization",
    "falsa bifurcation",
    "faux sillogisme",
    "sophisme",
    "paralogisme",  # generic — only flags when paired with a score
)

# Narrative verbs (French + a few English) anchoring a framework to a beat.
# Presence of one of these in the same line means the framework is *woven* into
# a sentence, not dropped as a bare list entry. Inflected common forms only.
# NB: deliberately excludes words that are common RHETORICAL SUBSTANTIVES too
# (``attaque``, ``forme``, ``présente``…) — a bare ref like "ASPIC+ : attaque
# (score 0.65)" cites a framework + score + the noun "attaque", and must still
# count as bare. Being strict here is the honest default (spec §4): better to
# flag a residual enumeration than to mask one behind an ambiguous token.
_NARRATIVE_VERBS = (
    "confirme",
    "invalide",
    "valide",
    "montre",
    "prouve",
    "démontre",
    "isole",
    "défait",
    "appuie",
    "soutient",
    "implique",
    "révèle",
    "suggère",
    "indique",
    "établit",
    "repose",
    "résulte",
    "découle",
    "signifie",
    "traduit",
    "reflète",
    "expose",
    "illustre",
    "incarne",
    "matérialise",
    "concrétise",
    "ancré",
    "ancrée",
    "ancrés",
    "ancrées",
    "cite",
    "citee",
    "confirmé",
    "invalidé",
    "prouvé",
    # auxiliaries / copulas — a sentence with "est/sont + [substantive]" is prose
    "n'est",
    "qu'un",
    "qu'une",
    "c'est",
    "il s'agit",
    "il s’agit",
    "permet",
    "explique",
    "justifie",
    "fonde",
    "garantit",
    "entraîne",
    "provient",
    "emprunte",
    "relève",
    "constitue",
)

# An isolated score: a float in [0, 1], alone in parens or after a colon/label.
# Catches "(0.8)", "(score 0.8)", "confiance: 0.8", ": 0.85". Rejects years /
# large numbers and version strings. Word-boundaried to avoid matching inside
# identifiers.
_SCORE_RE = re.compile(
    r"(?:\(?\s*(?:score|confiance|poids|severity|sévérité|confidence)\s*[:=]?\s*)?"
    r"0?\.\d{1,2}\b"
)
# but only count it when clearly a standalone metric — require a paren or a
# label prefix, to avoid flagging "0.5" inside a normal sentence by accident.
_STANDALONE_SCORE_RE = re.compile(
    r"\(\s*0?\.\d{1,2}\s*\)"  # (0.8)
    r"|\(?\s*(?:score|confiance|poids|confidence|sévérité)\s*[:=]?\s*0?\.\d{1,2}\b"  # score 0.8
)

# A numbered enumeration heading the dimensional dump uses — "Sophisme 1:",
# "Argument 2:", "Sophisme N". Repeated (> threshold) inside an act = the act
# degenerated into a dimension list.
_DUMP_HEADING_RE = re.compile(
    r"^\s*#{0,6}\s*(?:Sophisme|Argument|Dimension|Phase)\s+\d+\s*[:\-—]?",
    re.IGNORECASE | re.MULTILINE,
)


# --- verdict ------------------------------------------------------------------


@dataclass
class GateVerdict:
    """Honest verdict of the readability gate.

    ``band`` is one of ``PASS`` / ``WARN`` / ``FAIL``:

    * **PASS** — every act is present and non-trivial, no enumeration smell.
    * **WARN** — present and readable, but a small number of bare framework
      references remain (residual enumeration). Reported, not blocked.
    * **FAIL** — a structural problem: a missing act, a manifest enumeration
      (many bare refs or repeated dump headings), or (if injected) a failed
      reader-check. The report is not considered readable.

    ``reasons`` are specific and human-readable (which act, how many bare refs,
    which questions the reader failed) so the verdict is auditable, not a black
    box.
    """

    band: str
    reasons: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True for PASS/WARN (report is readable); False for FAIL."""
        return self.band in ("PASS", "WARN")

    def merge(self, other: "GateVerdict") -> "GateVerdict":
        """Combine two verdicts — the worse band wins, reasons accumulate."""
        order = {"PASS": 0, "WARN": 1, "FAIL": 2}
        worst = self if order[self.band] >= order[other.band] else other
        return GateVerdict(band=worst.band, reasons=[*self.reasons, *other.reasons])


# --- detector -----------------------------------------------------------------

# A line is flagged as a bare framework ref when it carries a framework term
# AND a standalone score AND none of the narrative verbs. Thresholds below
# decide WARN vs FAIL.
_BARE_WARN_THRESHOLD = 2  # 1–2 bare refs → WARN (residual)
_BARE_FAIL_THRESHOLD = 3  # ≥3 → FAIL (manifest enumeration)
_DUMP_FAIL_THRESHOLD = 2  # ≥2 repeated dump headings in one act → FAIL


def _line_has_framework(line: str) -> bool:
    low = line.lower()
    # solver / scheme family
    if any(k in low for k in _FRAMEWORK_SOLVERS):
        return True
    # fallacy name (word-bounded for the generic ones to limit false positives)
    for name in _FALLACY_NAMES:
        if name in low:
            return True
    return False


def _line_is_bare(line: str) -> bool:
    """A bare framework reference: framework cited + isolated score, no verb."""
    if not _line_has_framework(line):
        return False
    if not _STANDALONE_SCORE_RE.search(line):
        return False
    low = line.lower()
    if any(v in low for v in _NARRATIVE_VERBS):
        return False  # woven into a sentence — not bare
    return True


def _count_dump_headings(markdown: str) -> int:
    return len(_DUMP_HEADING_RE.findall(markdown))


class ReadabilityGate:
    """Deterministic structural check of a restitution report (spec §4).

    Construct with tuned thresholds (defaults follow the spec), then call
    :meth:`check_acts` (on the three acts) or :meth:`check_body` (on the
    assembled narrative body, i.e. the three acts concatenated, *excluding*
    the engineering appendix). The two are meant to be merged into one final
    verdict by the renderer.
    """

    def __init__(
        self,
        *,
        bare_warn_threshold: int = _BARE_WARN_THRESHOLD,
        bare_fail_threshold: int = _BARE_FAIL_THRESHOLD,
        dump_fail_threshold: int = _DUMP_FAIL_THRESHOLD,
        reader_check: Optional[Callable[[str], "ReaderCheckResult"]] = None,
    ):
        self.bare_warn_threshold = bare_warn_threshold
        self.bare_fail_threshold = bare_fail_threshold
        self.dump_fail_threshold = dump_fail_threshold
        self._reader_check = reader_check

    # -- structural checks ----------------------------------------------------

    def check_acts(self, acts: RestitutionActs) -> GateVerdict:
        """Check the three acts for presence, weaving, and non-dump."""
        reasons: List[str] = []
        worst_band = "PASS"

        total_bare = 0

        for n in (1, 2, 3):
            text = acts.as_dict()[n] or ""
            title = {1: "Acte I", 2: "Acte II", 3: "Acte III"}[n]

            # (1) presence — an act must exist and be non-trivial
            if acts.is_missing(n):
                reasons.append(
                    f"{title} absent — le rapport n'est pas complet "
                    f"(générateur non câblé ou acte vide)."
                )
                worst_band = _worsen(worst_band, "FAIL")
                continue

            # (2) weaving — bare framework references per act
            bare_lines = [ln.strip() for ln in text.splitlines() if _line_is_bare(ln)]
            total_bare += len(bare_lines)
            if bare_lines:
                preview = bare_lines[0][:90]
                reasons.append(
                    f"{title}: {len(bare_lines)} référence(s) de cadre « nue(s) » "
                    f"(framework + score isolé, sans ancrage narratif — spec §4). "
                    f"Ex: « {preview} »."
                )

            # (3) non-dump — repeated numbered dimension headings = enumeration
            dump_n = _count_dump_headings(text)
            if dump_n >= self.dump_fail_threshold:
                reasons.append(
                    f"{title}: {dump_n} titres de type « Sophisme N: / Argument N: » "
                    f"détectés — l'acte a dégénéré en énumération dimensionnelle."
                )
                worst_band = _worsen(worst_band, "FAIL")

        # aggregate bare refs across acts → WARN/FAIL by threshold
        if total_bare >= self.bare_fail_threshold:
            worst_band = _worsen(worst_band, "FAIL")
        elif total_bare >= self.bare_warn_threshold:
            worst_band = _worsen(worst_band, "WARN")

        return GateVerdict(band=worst_band, reasons=reasons)

    def check_body(self, body: str) -> GateVerdict:
        """Check the assembled narrative body (3 acts concatenated, no appendix).

        Runs the same bare-ref / dump detection on the joined text, plus the
        optional reader-check when one was injected.
        """
        reasons: List[str] = []
        worst_band = "PASS"

        bare_lines = [ln.strip() for ln in body.splitlines() if _line_is_bare(ln)]
        if len(bare_lines) >= self.bare_fail_threshold:
            worst_band = _worsen(worst_band, "FAIL")
            reasons.append(
                f"Corps: {len(bare_lines)} références de cadre nues (énumération "
                f"manifeste, spec §4)."
            )
        elif len(bare_lines) >= self.bare_warn_threshold:
            worst_band = _worsen(worst_band, "WARN")
            reasons.append(
                f"Corps: {len(bare_lines)} références de cadre nues résiduelles."
            )

        if _count_dump_headings(body) >= self.dump_fail_threshold:
            worst_band = _worsen(worst_band, "FAIL")
            reasons.append("Corps: titres d'énumération dimensionnelle détectés.")

        if self._reader_check is not None:
            result = self._reader_check(body)
            if not result.passed:
                worst_band = _worsen(worst_band, "FAIL")
                reasons.append(
                    f"Reader-check (lecteur non-spécialiste) échoué sur "
                    f"{result.failed_questions}/{result.total_questions} "
                    f"question(s) de compréhension."
                )
            else:
                reasons.append(
                    f"Reader-check passé ({result.total_questions}/{result.total_questions})."
                )

        return GateVerdict(band=worst_band, reasons=reasons)

    def check(self, acts: RestitutionActs) -> GateVerdict:
        """Full verdict: per-act structural check merged with the body check."""
        by_acts = self.check_acts(acts)
        # body excludes any act that is missing (honest — we don't gate on gaps
        # twice, the per-act check already FAILs those).
        body = "\n\n".join(
            (acts.as_dict()[n] or "") for n in (1, 2, 3) if not acts.is_missing(n)
        )
        by_body = self.check_body(body)
        return by_acts.merge(by_body)


# --- reader-check (optional, injected) ----------------------------------------


@dataclass
class ReaderCheckResult:
    """Outcome of an optional 0-shot reader comprehension probe (#1140).

    ``passed`` is True iff the reader answered all comprehension questions
    correctly enough. The gate treats a failed reader-check as a structural
    FAIL — an illegible report cannot pass readability, no matter how well
    woven its sentences are in isolation.
    """

    passed: bool
    total_questions: int
    failed_questions: int
    notes: str = ""


def _worsen(current: str, candidate: str) -> str:
    """Return the worse of two bands (PASS < WARN < FAIL)."""
    order = {"PASS": 0, "WARN": 1, "FAIL": 2}
    return candidate if order[candidate] > order[current] else current
