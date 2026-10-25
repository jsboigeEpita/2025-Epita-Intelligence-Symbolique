"""Why a formal theory is inconsistent — a cause the narrative can read.

FOL leg (#3107): the render used to be handed one fact — ``consistent:
False`` — and no cause, so the acts supplied their own: on a two-speaker
document, two speakers' opposite claims written into ONE theory read as
"Speaker_A's reasoning is invalidated", and the synthesis pinned the failure
on "quantifier scope" while the contradiction sat between two GROUND literals.

PL leg (#3122): the twin defect on a bare ``satisfiable: False``. The R1104
entry held 38 formulas with 0 complementary unit pairs — the contradiction
spread over implication chains — so no syntactic pair can name it. The core
comes from a deletion-based MUS instead, and the SAME classes, decision
spirit and phrasing classify it. One shared classifier, not a copy: only the
front-end differs (a ground-pair scan for FOL, a minimal core for PL).

This module computes the cause from the formulas themselves and from where
each formula came from (the source unit, and the speaker when an extractor
recorded one). The vocabulary deliberately contains no "quantifier" cause: an
inconsistency is only ever attributed to a quantifier scope by an inference
from *absence*, and a ground contradictory pair is a positive fact that rules
that inference out.

What is claimed, and what is not:

* ``between_voices`` — conflicting formulas resolving to TWO DIFFERENT KNOWN
  speakers (a ground ``P``/``¬P`` pair for FOL; core formulas from different
  speakers' units for PL). Each speaker's own reasoning is untouched: what
  the theory records is that they disagree.
* ``self_contradiction`` — a conflict inside ONE known speaker (or one
  identified source unit). This is a real finding about that voice and it must
  survive (#1019: never suppress an inconsistent verdict).
* ``between_sources`` — a conflict between separable source-unit groups whose
  speakers are NOT known. Saying "voices" there would be a fabrication; the
  unit ids are the honest boundary.
* ``batch_attribution`` — conflicting formulas that share one translation
  batch (up to 3 texts in one prompt), so the source unit of each formula is
  not knowable: the attribution is named as coarse, never upgraded.
* ``unattributed_side`` — a conflict where one side carries source units and
  the OTHER carries none (#3199). The sourceless formula belongs to no batch
  and no unit, so no attribution may cover the whole conflict — a fortiori
  never ``batch_attribution``. The known side is recorded in ``pairs``, the
  class says the boundary; a rung that names a speaker or a batch over a
  sourceless side would be exactly the over-attribution this class refuses.
* ``undetermined`` — an inconsistency whose conflict site could not be
  established (no ground pair for FOL; no known source unit for PL). It says
  so; it does not name a cause it cannot see (and the acts must not, either).

The FOL parse is intentionally narrow. A formula counts as a ground literal
only when the WHOLE formula is a predicate applied to constants — no
quantifier, no variable (uppercase head), no function symbol, no connective.
Anything else is "not ground", which can only weaken the claim to
``undetermined``.
"""

from __future__ import annotations

import re
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)

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

        if not (pos_sources and neg_sources):
            # #3199 — at least one side of the pair carries no source unit:
            # it belongs to no batch and no unit, so no attribution rung
            # (voices, one unit, batch) may cover the conflict. The empty
            # set used to fall through to ``batch_attribution``, claiming a
            # shared batch a sourceless formula cannot share — and a batch
            # of several speakers even read as ``between_voices``. The known
            # flank stays in ``sources``; both sides empty keeps the
            # historical coarse reading.
            if pos_sources or neg_sources:
                cause = "unattributed_side"
            else:
                cause = "batch_attribution"
        elif len(all_speakers) >= 2 and (pos_speakers != neg_speakers):
            cause = "between_voices"
        elif len(all_speakers) == 1 and len(pos_sources) == 1 and len(neg_sources) == 1:
            cause = "self_contradiction"
        elif not (pos_sources & neg_sources):
            cause = "between_sources"
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
        "unattributed_side",
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


def mus_by_deletion(
    formulas: Sequence[Any],
    is_unsat: Callable[[Sequence[Any]], bool],
) -> List[int]:
    """Indices of a minimal unsatisfiable core, by deletion (#3122).

    Walks the formulas in index order and permanently drops each one whose
    removal leaves the rest UNSAT. Costs at most one oracle call per formula —
    the issue's bound (38 formulas ⇒ ≤ 38 calls); the caller has already
    established the full set UNSAT (its verdict is the entry ticket, mirroring
    #3107's ``_cause_for`` gating), so no extra confirmation call is spent.

    Minimality holds by monotonicity: a removal that was refused (the rest
    became SAT) stays refused in every smaller remainder, because any subset
    of a satisfiable set is satisfiable. What is NOT guaranteed is uniqueness
    — the deletion order picks one MUS among possibly many.
    """
    core = list(range(len(formulas)))
    for i in range(len(formulas)):
        if i not in core:
            continue  # already dropped
        candidate = [j for j in core if j != i]
        if not candidate:
            break  # a one-formula core: nothing left to try
        if is_unsat([formulas[j] for j in candidate]):
            core = candidate
    return core


def classify_pl_inconsistency(
    formulas: Sequence[Any],
    formula_sources: Optional[Sequence[Any]] = None,
    speaker_by_unit: Optional[Mapping[str, Any]] = None,
    core_indices: Optional[Sequence[int]] = None,
    is_unsat: Optional[Callable[[Sequence[Any]], bool]] = None,
) -> Dict[str, Any]:
    """Name the cause of an UNSAT propositional theory (#3122) — PL twin of
    :func:`classify_inconsistency`, sharing its classes, helpers and phrasing.

    ``formula_sources`` and ``speaker_by_unit`` carry the same contract as the
    FOL leg. The conflict site is a minimal unsatisfiable core, not a ground
    pair: pass ``core_indices`` when the caller computed one, or ``is_unsat``
    to have it computed here by :func:`mus_by_deletion` (≤ one call per
    formula). Neither ⇒ the whole theory is the honest boundary and
    ``mus`` is ``False`` — coarse, never invented.

    The decision ladder generalises the FOL pair ladder to N sides (one per
    core formula): a side with no source unit voids every attribution rung
    (#3199 ``unattributed_side`` — the sourceless formula belongs to no
    batch, speaker or unit); otherwise two different known speaker-sets beat
    everything (``between_voices``); exactly one known speaker, or every
    core formula inside one unit, is ``self_contradiction``; source-unit
    groups that no formula straddles are ``between_sources``; entangled
    groups stay ``batch_attribution``; no known unit at all is
    ``undetermined``.
    """
    formula_sources = list(formula_sources or [])
    speaker_by_unit = dict(speaker_by_unit or {})
    n = len(formulas)
    if core_indices is None:
        core = (
            mus_by_deletion(formulas, is_unsat)
            if is_unsat is not None
            else list(range(n))
        )
    else:
        core = [i for i in core_indices if 0 <= i < n]
    # A core backed by a deletion computation (here or by the caller); False
    # only on the degraded whole-theory path, where nothing was minimised.
    mus = core_indices is not None or is_unsat is not None

    sides: List["frozenset[str]"] = [
        _as_source_set(formula_sources[i]) if i < len(formula_sources) else frozenset()
        for i in core
    ]
    speaker_sets: List["set[str]"] = [
        _speakers_of(side, speaker_by_unit) for side in sides
    ]
    known_sides = [side for side in sides if side]
    all_units: "set[str]" = set()
    for side in known_sides:
        all_units |= set(side)
    all_speakers: "set[str]" = set()
    for speakers in speaker_sets:
        all_speakers |= speakers
    distinct_speaker_sets = {frozenset(s) for s in speaker_sets if s}

    pseudo_sources: List[List[str]] = [[], []]
    pseudo_speakers: List[List[str]] = [[], []]
    if not known_sides:
        cause = "undetermined"
    elif len(sides) != len(known_sides):
        # #3199 — a core side carries no source unit: the sourceless formula
        # belongs to no batch, speaker or unit, so no attribution rung may
        # cover the conflict. ``known_sides`` filtering used to drop the
        # empty side from the ladder entirely, leaving one known component
        # that read as ``batch_attribution`` (or absorbed the conflict into
        # one speaker's ``self_contradiction``) — an over-attribution. The
        # known flank is recorded on the first side of ``pairs``.
        cause = "unattributed_side"
        pseudo_sources = [sorted(all_units), []]
        pseudo_speakers = [sorted(all_speakers), []] if all_speakers else [[], []]
    elif len(distinct_speaker_sets) >= 2:
        # Two sides attribute to different speaker sets: they disagree —
        # the FOL ``pos_speakers != neg_speakers`` condition, generalised.
        cause = "between_voices"
        first, second = sorted(distinct_speaker_sets)[:2]
        pseudo_speakers = [sorted(first), sorted(second)]
        pseudo_sources = [
            sorted(
                {
                    u
                    for side, sp in zip(sides, speaker_sets)
                    if frozenset(sp) == first
                    for u in side
                }
            ),
            sorted(
                {
                    u
                    for side, sp in zip(sides, speaker_sets)
                    if frozenset(sp) == second
                    for u in side
                }
            ),
        ]
    elif len(all_speakers) == 1 or len(all_units) == 1:
        # One voice contradicting itself across their own units (FOL parity),
        # or a core confined to one unit with no speaker recorded.
        cause = "self_contradiction"
        (sp,) = sorted(all_speakers) if all_speakers else (None,)
        pseudo_speakers = [[sp]] if sp else [[], []]
        pseudo_sources = [sorted(all_units), []]
    else:
        # Connected components of the side-overlap graph: groups no formula
        # straddles are separable sources; one entangled component is a batch.
        components: Dict[int, "set[str]"] = {}
        parent = list(range(len(known_sides)))

        def _find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i, side in enumerate(known_sides):
            for j in range(i):
                if side & known_sides[j]:
                    parent[_find(i)] = _find(j)
        for i, side in enumerate(known_sides):
            components.setdefault(_find(i), set()).update(side)
        if len(components) >= 2:
            cause = "between_sources"
            group_a, group_b = sorted(components.values(), key=sorted)[:2]
            pseudo_sources = [sorted(group_a), sorted(group_b)]
        else:
            cause = "batch_attribution"
            pseudo_sources = [sorted(all_units), []]

    return {
        "cause": cause,
        "ground": False,  # no ground-pair mechanism on this leg — the core is
        "mus": mus,
        "core": {"size": len(core), "indices": list(core)},
        "pairs": (
            [
                {
                    "sources": pseudo_sources,
                    "speakers": pseudo_speakers,
                    "cause": cause,
                }
            ]
            if cause != "undetermined"
            else []
        ),
        "formulas": n,
        "units_known": bool(known_sides),
        "speakers_known": bool(speaker_by_unit),
    }


# Short labels, one per class of the vocabulary. #3199 : the roles statement
# names the cause inside a bounded statement (``_STATEMENT_CAP``), where the
# full ``cause_phrase`` does not fit — and it must be readable prose, never
# the enum token (a reader cannot charge anyone from « (unattributed_side) »).
# Same module as ``cause_phrase`` so the vocabulary keeps ONE home; a class
# this table does not know renders its token, which stays honest.
_CAUSE_SHORT_LABELS = {
    "between_voices": "contradiction entre voix",
    "self_contradiction": "auto-contradiction d'une même voix",
    "between_sources": "contradiction entre unités sources",
    "batch_attribution": "contradiction interne à un lot de traduction",
    "unattributed_side": "contradiction dont un côté est sans unité source",
    "undetermined": "inconsistance sans cause établie",
}


def cause_short_label(cause: Any) -> str:
    """Readable short label of a stated cause, for a bounded statement.

    ``cause`` is the record's ``consistency_cause`` mapping (or the bare
    class string). Empty string when no cause was stated — the caller renders
    the unqualified form rather than a label for something never measured.
    """
    if isinstance(cause, dict):
        kind = cause.get("cause")
    else:
        kind = cause
    if not kind:
        return ""
    kind = str(kind)
    return _CAUSE_SHORT_LABELS.get(kind, kind)


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
    elif kind == "unattributed_side":
        # Known flank named speaker-first, unit as fallback — the same
        # convention as ``self_contradiction``'s ``who``.
        who = [s for side in speakers for s in side] or [
            u for side in sources for u in side
        ]
        known = f" (côté connu : {', '.join(sorted(set(who)))})" if who else ""
        phrase = (
            "contradiction dont un côté est sans unité source"
            f"{known} — ce côté du conflit n'appartient à aucun lot ni "
            "locuteur documenté par ce run"
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
    # #3122 — the PL leg's stated mechanism: the core is a positive fact (a
    # minimal unsatisfiable subset), the same way a ground pair is for FOL.
    core = cause.get("core")
    if cause.get("mus") and isinstance(core, dict) and core.get("size"):
        phrase += (
            f"; cœur minimal d'insatisfaisabilité ({core['size']} formule(s))"
            " — en retirer une quelconque rend l'ensemble satisfiable"
        )
    return phrase


# #3237 — the cause rule both acts' prompts carry, from this module (the
# cause vocabulary's one home, the same shape as ``SPEAKER_NAMING_RULE``).
# Act III stated it inline since #3107; Act II received the recorded causes on
# its evidence lines but not the rule that binds the prose to them, and it is
# the act that misstated the cause (R1110c: a formal contradiction whose
# recorded cause is ``between_sources`` told the reader « le point où les
# deux voix se heurtent »). One rule, one father — the acts import, they
# never copy, so no second wording can drift.
FORMAL_CAUSE_NAMING_RULE = (
    "Quand une théorie du premier ordre est inconsistante, ou que "
    "l'encodage propositionnel est insatisfiable, DIS LA CAUSE que le "
    "constat porte (elle est écrite dans CE QUE LES CADRES STRUCTURÉS "
    "ÉTABLISSENT : « contradiction entre voix », « auto-contradiction "
    "de … », « contradiction entre unités sources », « cause non "
    "établie ») ; n'attribue jamais cette inconsistance au raisonnement "
    "d'un locuteur en particulier, et jamais à la portée des "
    "quantificateurs quand la cause porte une paire de littéraux ground."
)
