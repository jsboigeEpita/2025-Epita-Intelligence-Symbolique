"""Why a FOL theory is inconsistent — a cause the narrative can read (#3107).

The render used to be handed one fact — ``consistent: False`` — and no cause,
so the acts supplied their own: on a two-speaker document, two speakers'
opposite claims written into ONE theory read as "Speaker_A's reasoning is
invalidated", and the synthesis pinned the failure on "quantifier scope" while
the contradiction sat between two GROUND literals.

This module computes the cause from the formulas themselves and from where
each formula came from (the source unit, and the speaker when an extractor
recorded one). The vocabulary deliberately contains no "quantifier" cause: an
inconsistency is only ever attributed to a quantifier scope by an inference
from *absence*, and a ground contradictory pair is a positive fact that rules
that inference out.

What is claimed, and what is not:

* ``between_voices`` — a ground ``P``/``¬P`` pair whose formulas resolve to
  TWO DIFFERENT KNOWN speakers. Each speaker's own reasoning is untouched:
  what the theory records is that they disagree.
* ``self_contradiction`` — a ground pair inside ONE known speaker (or one
  identified source unit). This is a real finding about that voice and it must
  survive (#1019: never suppress an inconsistent verdict).
* ``between_sources`` — a ground pair from two different source units whose
  speakers are NOT known. Saying "voices" there would be a fabrication; the
  unit ids are the honest boundary.
* ``batch_attribution`` — a ground pair whose formulas share one translation
  batch (up to 3 texts in one prompt), so the source unit of each formula is
  not knowable: the attribution is named as coarse, never upgraded.
* ``undetermined`` — an inconsistency with no ground pair found. It says so;
  it does not name a cause it cannot see (and the acts must not, either).

The parse is intentionally narrow. A formula counts as a ground literal only
when the WHOLE formula is a predicate applied to constants — no quantifier, no
variable (uppercase head), no function symbol, no connective. Anything else is
"not ground", which can only weaken the claim to ``undetermined``.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

#: A predicate applied to constants, the whole formula being that application.
_GROUND_LITERAL = re.compile(
    r"^(?P<pred>[A-Za-z_À-ÖØ-öø-ÿ]" r"[A-Za-z0-9_À-ÖØ-öø-ÿ]*)" r"\((?P<args>[^()]*)\)$"
)
#: A constant argument: lowercase or digit start (uppercase = a FOL variable).
_CONSTANT_ARG = re.compile(r"^[a-z0-9_][A-Za-z0-9_]*$")


def ground_literal(formula: Any) -> Optional[Tuple[str, bool]]:
    """``(atom, polarity)`` when the formula is a ground literal, else None.

    ``"P(a)"`` -> ``("P(a)", True)``; ``"!P(a, b)"`` -> ``("P(a,b)", False)``.
    Whitespace is normalised out of the atom so two spellings of the same
    literal compare equal.
    """
    if not isinstance(formula, str):
        return None
    text = formula.strip()
    polarity = True
    while text and text[0] in ("!", "¬", "~"):
        polarity = not polarity
        text = text[1:].strip()
    if not text:
        return None
    match = _GROUND_LITERAL.match(text)
    if not match:
        return None
    args = [a.strip() for a in match.group("args").split(",") if a.strip()]
    if not args:
        return None
    for arg in args:
        if not _CONSTANT_ARG.match(arg):
            # A variable (X), a function symbol (f(x)) or anything else: not ground.
            return None
    atom = f"{match.group('pred')}({','.join(args)})"
    return atom, polarity


def ground_contradiction_pairs(formulas: Sequence[Any]) -> List[Dict[str, Any]]:
    """Direct ``P(…)`` / ``¬P(…)`` pairs on the SAME atom, by formula index."""
    positives: Dict[str, List[int]] = {}
    negatives: Dict[str, List[int]] = {}
    for index, formula in enumerate(formulas):
        parsed = ground_literal(formula)
        if parsed is None:
            continue
        atom, polarity = parsed
        (positives if polarity else negatives).setdefault(atom, []).append(index)
    pairs: List[Dict[str, Any]] = []
    for atom, pos_indices in positives.items():
        for neg_index in negatives.get(atom, []):
            for pos_index in pos_indices:
                pairs.append(
                    {
                        "atom": atom,
                        "positive_index": pos_index,
                        "negative_index": neg_index,
                    }
                )
    pairs.sort(key=lambda p: (p["positive_index"], p["negative_index"]))
    return pairs


def count_quantified(formulas: Sequence[Any]) -> int:
    """Formulas carrying a quantifier — the share a scope reading would need."""
    return sum(
        1
        for f in formulas
        if isinstance(f, str) and re.search(r"\b(forall|exists)\b|[∀∃]", f)
    )


def _as_source_set(source: Any) -> "frozenset[str]":
    """One formula's source unit ids, never a single id silently split."""
    if isinstance(source, str):
        return frozenset([source]) if source else frozenset()
    if isinstance(source, Iterable):
        return frozenset(str(s) for s in source if s)
    return frozenset()


def _speakers_of(
    units: Iterable[str], speaker_by_unit: Mapping[str, Any]
) -> "set[str]":
    found: "set[str]" = set()
    for unit in units:
        speaker = speaker_by_unit.get(unit)
        if isinstance(speaker, str) and speaker.strip():
            found.add(speaker.strip())
    return found


def classify_inconsistency(
    formulas: Sequence[Any],
    formula_sources: Optional[Sequence[Any]] = None,
    speaker_by_unit: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Name the cause of an inconsistent theory, from facts the run holds.

    ``formula_sources`` is aligned with ``formulas``: entry *i* names the
    source unit id(s) formula *i* was translated from (a list — a translation
    batch of several texts names them all, because the model was not asked to
    separate them). ``speaker_by_unit`` maps a unit id to a speaker, and holds
    only what an extractor actually recorded.

    Returns a dict — see the module docstring for the cause vocabulary — that
    a writer stores beside the verdict and a renderer phrases with
    :func:`cause_phrase`.
    """
    formula_sources = list(formula_sources or [])
    speaker_by_unit = dict(speaker_by_unit or {})
    pairs = ground_contradiction_pairs(formulas)

    enriched: List[Dict[str, Any]] = []
    causes_seen: List[str] = []
    for pair in pairs:
        pos_sources = (
            _as_source_set(formula_sources[pair["positive_index"]])
            if pair["positive_index"] < len(formula_sources)
            else frozenset()
        )
        neg_sources = (
            _as_source_set(formula_sources[pair["negative_index"]])
            if pair["negative_index"] < len(formula_sources)
            else frozenset()
        )
        pos_speakers = _speakers_of(pos_sources, speaker_by_unit)
        neg_speakers = _speakers_of(neg_sources, speaker_by_unit)
        all_speakers = pos_speakers | neg_speakers

        if len(all_speakers) >= 2 and (pos_speakers != neg_speakers):
            cause = "between_voices"
        elif len(all_speakers) == 1 and len(pos_sources) == 1 and len(neg_sources) == 1:
            cause = "self_contradiction"
        elif pos_sources and neg_sources and not (pos_sources & neg_sources):
            cause = "between_sources"
        elif pos_sources and neg_sources:
            cause = "batch_attribution"
        else:
            cause = "batch_attribution"
        causes_seen.append(cause)
        enriched.append(
            {
                **pair,
                "sources": [sorted(pos_sources), sorted(neg_sources)],
                "speakers": [sorted(pos_speakers), sorted(neg_speakers)],
                "cause": cause,
            }
        )

    for candidate in (
        "between_voices",
        "self_contradiction",
        "between_sources",
        "batch_attribution",
    ):
        if candidate in causes_seen:
            cause = candidate
            break
    else:
        cause = "undetermined"

    return {
        "cause": cause,
        "ground": bool(pairs),
        "pairs": enriched,
        "quantified_formulas": count_quantified(formulas),
        "formulas": len(formulas),
        "units_known": any(_as_source_set(s) for s in formula_sources),
        "speakers_known": bool(speaker_by_unit),
    }


def cause_phrase(cause: Dict[str, Any]) -> str:
    """The French sentence fragment renderers print, derived from the cause.

    Never says "quantifier scope" for a ground contradiction: with a ground
    pair, the scope cannot be the cause, and the fragment says so explicitly
    (the render that pinned it there is the defect #3107 repairs).
    """
    kind = cause.get("cause")
    pairs = cause.get("pairs") or []
    first = pairs[0] if pairs else {}
    sources = first.get("sources") or [[], []]
    speakers = first.get("speakers") or [[], []]
    quantified = cause.get("quantified_formulas")
    total = cause.get("formulas")

    if kind == "between_voices":
        voices = " / ".join(sorted({s for side in speakers for s in side}))
        phrase = f"contradiction entre voix ({voices})"
    elif kind == "self_contradiction":
        who = [s for side in speakers for s in side] or [
            u for side in sources for u in side
        ]
        who_text = ", ".join(sorted(set(who))) or "une même unité source"
        phrase = f"auto-contradiction de {who_text}"
    elif kind == "between_sources":
        units = " / ".join(sorted({u for side in sources for u in side}))
        phrase = (
            "contradiction entre unités sources"
            + (f" ({units})" if units else "")
            + " — locuteurs non documentés par ce run"
        )
    elif kind == "batch_attribution":
        phrase = (
            "contradiction interne à un lot de traduction — l'unité source de "
            "chaque formule n'est pas séparable"
        )
    else:
        phrase = (
            "inconsistance sans paire de littéraux ground identifiée (cause non "
            "établie)"
        )

    if cause.get("ground"):
        phrase += "; paire de littéraux ground — la portée des quantificateurs n'y joue aucun rôle"
    elif quantified:
        phrase += f" ({quantified} formule(s) quantifiée(s) sur {total})"
    return phrase
