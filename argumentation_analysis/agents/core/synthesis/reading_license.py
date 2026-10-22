"""#3123 — what a synthesis may conclude from the artifacts it was handed.

Two misreadings were measured in the R1104 render, and both are an inference
the input never licensed:

* **breadth as robustness** — the grounded extension covered most of the
  arguments and the text called the argumentation robust, while the evaluated
  graph carried fewer attacks than arguments (edges were submitted and dropped
  before the frame was built). Breadth there measures the frame's sparsity,
  not the discourse's resistance to challenge.
* **someone else's inconsistency as the discourse's** — a theory was
  unsatisfiable between source units (``between_sources``) and the synthesis
  concluded that the discourse itself was incoherent, though no single voice
  was shown to contradict itself.
* **a check that decided nothing, sold as strength** (R1105b, Sonnet pass) —
  the FOL leg returned ``consistent`` without answering a single query; Act II
  of the same render said exactly that ("ran without distinguishing anything,
  and that is neither a strength nor a weakness") and the synthesis still
  called the discourse robust "at the level of formal consistency". A decided
  consistency with no inference behind it licenses no robustness claim; an
  entry that DID answer queries may still be cited as strength.

This module is the deterministic, non-LLM check over a PRODUCED text. It
flags; it never rewrites — the defect is the inference, and the sentence is
where a reader can see it. Every detector is a narrow phrase pattern, never a
bag of tokens, so a sentence that already carries its qualifier is not
flagged, and a negated robustness statement ("n'est pas robuste") is not a
claim at all.

No state writer is changed here: the caller stores the result beside the
value gates it already persists.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

#: A robustness word. Read together with :data:`_BREADTH_MARKERS`: alone it is
#: an ordinary adjective, and only the *combination* makes the claim.
_ROBUSTNESS_MARKERS = re.compile(
    r"(robust\w*|robustesse|solide(?:ment)?|solidité|résiste\w*|résilien\w*|"
    r"bien étay\w*|consolid\w*)",
    re.IGNORECASE,
)

#: A breadth word. ``extension`` alone names a computed object; combined with a
#: robustness word it becomes "the extension is broad, therefore the discourse
#: is robust" — the inference #3123 removes.
_BREADTH_MARKERS = re.compile(
    r"(extension\w*|grounded|groundée\w*|couvre\w*|étendue|large\w*|"
    r"breadth|broad\w*|comprehensive)",
    re.IGNORECASE,
)

#: A discourse-level subject: the sentence speaks about the discourse as a
#: whole (or about a speaker's commitments), not about a source unit. The
#: possessive forms below are the #3123/R1105c Act II shape — "the case the
#: speaker builds does not hold together" charges a recorded cause to the
#: speaker just as the explicit subjects do.
_DISCOURSE_SUBJECTS = re.compile(
    r"(le discours|l['’]ensemble des engagements|les engagements du discours|"
    r"les engagements (?:du|d['’]un) locuteur|s[ea]s engagements|"
    r"la position (?:est|s['’]avère|se révèle|reste)|"
    r"(?:le|la) (?:cas|thèse|these|démonstration|demonstration|argumentation|"
    r"raisonnement|argumentaire|défense|defense|fil|développement|"
    r"developpement) (?:que|qu['’]|de |du |d['’])|"
    r"the discourse|the speaker['’]s commitments|the commitments)",
    re.IGNORECASE,
)

#: An incoherence predicate.
_INCOHERENCE_MARKERS = re.compile(
    r"(incohér\w*|inconsisten\w*|contradictoire\w*|contradiction|"
    r"se contredis\w*|se contredit|"
    r"ne tient pas|does not hold|is inconsistent|is incoherent)",
    re.IGNORECASE,
)

#: The qualifiers the writer's own phrase carries (#3107/#3122). A sentence
#: that already names the conflict site is stating the cause, not misreading it.
_QUALIFIERS = re.compile(
    r"(entre unités sources|entre voix|auto[- ]contradiction|"
    r"lot de traduction|cause non établie|"
    r"between (?:source )?units|between voices|translation batch|"
    r"cause not established)",
    re.IGNORECASE,
)

#: A formal-consistency word. Combined with a robustness word it claims the
#: FOL leg as strength; whether that is licensed depends on what the leg
#: decided (see :func:`_fol_decisions`).
_FORMAL_CONSISTENCY_MARKERS = re.compile(
    r"(coh[ée]rence formelle|consistance formelle|vérification formelle|"
    r"formal consistency|formal(ly)? (?:consistent|sound|verification|check)|"
    r"formellement|test formel)",
    re.IGNORECASE,
)

_NEGATION = re.compile(r"\b(ne|n['’]|pas|jamais|sans|aucun\w*)\b", re.IGNORECASE)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text or "") if s.strip()]


def _is_negated(sentence: str, start: int) -> bool:
    """True when a negation sits just before ``start`` ("n'est pas robuste").

    A 32-character window keeps the test cheap and local: a negation further
    away belongs to another clause, and treating it as one would silence real
    claims that follow a negative aside.
    """
    window = sentence[max(0, start - 32) : start]
    return bool(_NEGATION.search(window))


def _dung_measurements(state: Any) -> List[Dict[str, Any]]:
    """The measured attack density of every Dung framework the state holds."""
    measurements: List[Dict[str, Any]] = []
    entries = getattr(state, "dung_frameworks", {}) or {}
    if not isinstance(entries, dict):
        return measurements
    for framework, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        arguments = entry.get("arguments") or []
        attacks = entry.get("attacks") or []
        if not isinstance(arguments, list) or not arguments:
            continue
        measurements.append(
            {
                "framework": framework,
                "arguments": len(arguments),
                "attacks": len(attacks) if isinstance(attacks, list) else 0,
                "density": (
                    len(attacks) / len(arguments) if isinstance(attacks, list) else 0.0
                ),
                "attacks_submitted": entry.get("attacks_submitted"),
                "attacks_retained": entry.get("attacks_retained"),
            }
        )
    return measurements


def _formal_causes(state: Any) -> List[str]:
    """The cause classes the run actually recorded, FOL and PL alike."""
    causes: List[str] = []
    for attribute in ("fol_analysis_results", "propositional_analysis_results"):
        for result in getattr(state, attribute, []) or []:
            if not isinstance(result, dict):
                continue
            cause = result.get("consistency_cause")
            if isinstance(cause, dict) and cause.get("cause"):
                causes.append(str(cause["cause"]))
    return causes


def _fol_decisions(state: Any) -> Dict[str, int]:
    """What the FOL leg actually decided (#3123, R1105b instance).

    ``vacuous_consistent`` counts entries that returned ``consistent`` without
    answering a single inference — a decided consistency that distinguished
    nothing. ``decisive`` counts entries that answered queries or decided an
    inconsistency; as long as one exists, citing formal strength is licensed
    (the positive control).
    """
    vacuous = 0
    decisive = 0
    for result in getattr(state, "fol_analysis_results", []) or []:
        if not isinstance(result, dict):
            continue
        if result.get("consistent") is True and not (result.get("inferences") or []):
            vacuous += 1
        elif result.get("inferences") or result.get("consistent") is False:
            decisive += 1
    return {"vacuous_consistent": vacuous, "decisive": decisive}


def check_reading_license(
    text: str,
    state: Any,
    *,
    dense_threshold: float = 1.0,
    max_flags: int = 12,
) -> Dict[str, Any]:
    """Flag where a produced synthesis reads a qualifier as a conclusion.

    ``dense_threshold`` is the attack-density below which breadth is not
    robustness (one attack per argument). It is the same constant the briefing
    rule states, so the reader and the check never disagree.

    Returns ``{"flags": [...], "checked": {...}, "threshold": ...}``. An empty
    text yields no flag — nothing was produced, and an absent synthesis is
    already reported by its status, not by this check.
    """
    sentences = _sentences(text or "")
    measurements = _dung_measurements(state)
    causes = _formal_causes(state)
    fol_decisions = _fol_decisions(state)
    self_contradiction = "self_contradiction" in causes
    sparse_everywhere = bool(measurements) and all(
        m["density"] < dense_threshold for m in measurements
    )
    # The flags carry the sentence as produced — no slice: a cut could only
    # hide the qualifier the reader needs, and it never protected a verdict
    # (detection reads the whole sentence; #2850 asked what the cut was for,
    # and the answer was nothing).

    flags: List[Dict[str, Any]] = []
    for sentence in sentences:
        if len(flags) >= max_flags:
            break

        # -- breadth sold as robustness -------------------------------------
        robustness = _ROBUSTNESS_MARKERS.search(sentence)
        if (
            robustness is not None
            and _BREADTH_MARKERS.search(sentence) is not None
            and not _is_negated(sentence, robustness.start())
            and sparse_everywhere
        ):
            flags.append(
                {
                    "kind": "breadth_as_robustness",
                    "sentence": sentence,
                    "measured": {
                        "threshold": dense_threshold,
                        "frameworks": measurements,
                    },
                }
            )
            continue

        # -- a check that decided nothing, sold as strength (R1105b) --------
        if (
            robustness is not None
            and _FORMAL_CONSISTENCY_MARKERS.search(sentence) is not None
            and not _is_negated(sentence, robustness.start())
            and fol_decisions["vacuous_consistent"] > 0
            and fol_decisions["decisive"] == 0
        ):
            flags.append(
                {
                    "kind": "vacuous_consistency_as_strength",
                    "sentence": sentence,
                    "measured": {"fol": fol_decisions},
                }
            )
            continue

        # -- a cause misread as the discourse's ------------------------------
        if (
            _DISCOURSE_SUBJECTS.search(sentence) is not None
            and _INCOHERENCE_MARKERS.search(sentence) is not None
            and _QUALIFIERS.search(sentence) is None
            and not self_contradiction
        ):
            flags.append(
                {
                    "kind": "discourse_incoherence",
                    "sentence": sentence,
                    "measured": {"recorded_causes": causes},
                }
            )

    return {
        "flags": flags,
        "checked": {
            "sentences": len(sentences),
            "dung_frameworks": len(measurements),
            "recorded_causes": causes,
            "self_contradiction_recorded": self_contradiction,
            "fol_decisions": fol_decisions,
        },
        "threshold": dense_threshold,
    }


def summarise_flags(report: Optional[Dict[str, Any]]) -> str:
    """One line a log or a gate verdict can print — never the text itself."""
    if not isinstance(report, dict):
        return ""
    flags = report.get("flags") or []
    if not flags:
        return ""
    kinds = sorted({str(f.get("kind")) for f in flags})
    return f"{len(flags)} reading-license flag(s): {', '.join(kinds)}"
