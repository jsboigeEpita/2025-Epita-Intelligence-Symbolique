"""A measured virtue is localised only on a unit the measure scored (#3358).

## The gap this closes

Paid pass R1134a: in Act III's « Comment se faire son avis », just above the
pipeline-rendered verdict, the prose advised two passages « car c'est là que
le discours est clair et que sa réfutation est constructive » — the
discourse's two measured virtues (clarté 6/8, réfutation constructive 6/8),
localised onto passages. One passage held both virtues at the top band; the
other was **never among the evaluated units**. The reader was told the
measured virtues live in a passage the measure never read.

The root cause is a data gap: the base prompt carries the strengths
DISCOURSE-level (k arguments at the top band of m evaluated) and never the
per-unit virtue table, so the writer cannot know a passage is unscored.
Same family as #3297/#3343 — an instruction without an instrument, and a
writer without the data to comply even if it wanted to.

## The census, measured before the gesture was chosen

On this seat's stored Act III strings (3 local corpora, 103 states with a
« que faire » beat): **3 sentences localise a virtue** under the coarse
rule (virtue vocabulary + locative), 2 distinct shapes — one ordinary
adjective (« pertinent » qualifying objections, not the measured virtue)
and one true class localising clarté onto « le passage central » by
description. The recorded shape lives on the coordinator's seat. The class
is rare (~1/103 locally) — and the recorded case is a **mixed bundle**:
one passage holds the virtues, the other never read them. A clause drop
would kill the true half with the false one, and localising a virtue on
a unit that holds it is the GOOD behavior (anti-pendulum). The gesture is
therefore the #3343 bounded retry, with the per-unit table in the
correction — the data the base prompt never had.

## The rule

A sentence is read when it carries BOTH:

- vocabulary of a virtue that **passed the discourse bar** — the #3335
  ``_VIRTUE_PROSE_RE`` mapping, bounded by the passed set exactly as
  ``restated_verdict_sentences`` bounds it (injected by the caller, never
  duplicated — one mapping, one place); and
- a unit designation trigger: a named unit id (``arg_N``) or a
  localising locative (« c'est là que », « dans le/ce passage »).

The units the sentence designates are then resolved **the way production
prose can actually designate** (measured: the stored acts carry 0 ``arg_N``
— the readability gate forbids printing one, #2980 — and 0 of the census
sentences resolve by content, so nothing measured is silently cleared):

- a named ``arg_N`` (the synthetic path — robustness, prose never carries
  it), or
- a **content designation**: a run of ``>= 4`` consecutive letter tokens
  from an evaluated-unit's text, verbatim in the sentence. Deterministic
  and bounded — no model call; the retry's legend hands the writer each
  unit's text, so a rewrite CAN reach this path, and the reader can see
  the designation it rests on.

The sentence stands only when every designated unit is among the evaluated
units AND holds every carried virtue at the instrument's top band
(``>= 1.0``, the ``_STRENGTH_MIN_SCORE`` of ``_collect_quality_strengths``).
A locative that designates nothing resolvable is unbacked by construction
— flagged (the recorded shape: passages designated by description, « le
passage central »). A Greek letter is deliberately NOT a designation path:
the legend lives in the prompt only (#3317), a printed letter is a leak
the draft comparison counts, never a referent the check resolves.

## What is licensed, and what is not

- a **discourse-level** claim (« le discours est clair », no unit id, no
  locative) is the pipeline verdict's own ground (#3159) — never food;
- a **weakness statement is not an attribution**: a negation or inverse
  marker within 30 characters before the virtue word cancels the carry —
  « le point le moins clair », « manque de clarté », « ne réfute pas » say
  the unit LACKS the virtue. ``plus`` is deliberately NOT a marker: « le
  plus clair » still attributes;
- vocabulary of a virtue the bar rejected never fires (bounded by the
  passed set — #3335's calibration: an act discussing « les sources » when
  no source virtue passed is never touched);
- localising a virtue on a unit that **holds** it is the good behavior —
  the positive control, untouched, and reachable in the production shape
  (content designation, no id in the prose).

## Honesty contract (#1019, #3249)

The check only ever reports; it never rewrites. The motive is a code
literal with counts, never a quote of the prose; the sentences themselves
go to the trace log, where the neighbouring repairs already log their
excerpts. The note names exactly what was judged — a localisation with no
measured unit behind it — so it never fires on a sentence the check could
not read: every flagged sentence either names/designates a unit the table
contradicts, or designates nothing the state can resolve at all. The
repair is the #3343 bounded ONE retry: the correction carries the flagged
sentences AND the per-unit table, routed through the writer's relabel seam
so no raw id ever reaches the writer; the rewrite is kept only when the
summed flag count (this check + #3297's) AND the readability leak count
(#2980 ids + #3317 letters) drop together.
"""

from __future__ import annotations

import re
from typing import Dict, List, Mapping, Optional, Sequence

#: The localising locatives, as the recorded and census shapes write them:
#: « car c'est là que le discours est clair » (paid pass R1134a) and « la
#: distinction posée dans le passage central » (local census hit). Narrow on
#: purpose — each form is measured in the wild before it joins the set.
_LOCATIVE = re.compile(
    r"c['’]est\s+l[àa]\s+que|dans\s+(?:le|ce|cet|la)\s+passage",
    re.IGNORECASE,
)

#: A named unit, as Act III prose names ids (weak points, counters, claims
#: blocks all key by it). Production prose never prints one (#2980) — the
#: path stays for robustness and for the synthetic witnesses.
_UNIT_ID = re.compile(r"\barg_\d+\b")

#: A French letter token — the content-designation vocabulary. Accents and
#: ligatures included; digits and punctuation are noise on both sides.
_TOKEN = re.compile(r"[a-zà-öø-ÿœæ]+")

#: How many consecutive unit-text tokens a sentence must carry verbatim to
#: designate that unit. Four: short enough that a quoted clause reaches it,
#: long enough that ordinary French does not collide with it (measured: 0
#: of the census sentences resolve at 4 — the rule clears nothing it did
#: not measure).
_DESIGNATION_RUN = 4

#: Sentence split, the plugin's own idiom.
_SENTENCE = re.compile(r"\s*[^.!?\n]+[.!?]*")

#: A negation or inverse marker — the weakness half of the vocabulary.
#: ``plus`` is deliberately absent (see the module docstring). The marker is
#: matched unanchored and the window is judged by POSITION
#: (``_negated_before``), never by slicing the sentence: the census guard
#: (#2850) rightly flags slices as coverage windows, and this one bounds
#: nothing — the whole sentence is the one being judged.
_NEGATION = re.compile(
    r"\b(?:ne|n['’]|pas|moins|gu[èe]re|jamais|sans|manqu\w*|absence|peu"
    r"|aucun\w*|ni)\b",
    re.IGNORECASE,
)

#: How far BEFORE the virtue word a marker still cancels the carry.
_NEGATION_WINDOW = 30

#: The instrument's top band — a unit HOLDS a virtue at ``>= 1.0`` (the
#: ``_STRENGTH_MIN_SCORE`` of ``_collect_quality_strengths``; values above
#: from non-canonical writers still qualify).
_TOP_BAND = 1.0

#: The table shown to the retrying writer lists at most this many units.
_TABLE_CAP = 12


def flatten_unit_scores(quality: Mapping[str, object]) -> Dict[str, Dict[str, float]]:
    """``{arg_id: {virtue: score}}`` from the state's raw quality dict.

    Same parsing as ``_collect_quality_strengths``: the canonical writer key
    is ``scores`` (``shared_state.add_quality_score``), ``scores_par_vertu``
    is the legacy fallback, non-numeric values never reach the table.
    """
    flat: Dict[str, Dict[str, float]] = {}
    for arg_id, qs in (quality or {}).items():
        if not isinstance(qs, dict):
            continue
        spv = qs.get("scores")
        if not isinstance(spv, dict):
            spv = qs.get("scores_par_vertu")
        if not isinstance(spv, dict):
            continue
        flat[str(arg_id)] = {
            str(k): float(v) for k, v in spv.items() if isinstance(v, (int, float))
        }
    return flat


def _negated_before(sentence: str, start: int) -> bool:
    """True when a negation or inverse marker ends within the window before
    ``start`` — the same 30-character reading the vocabulary was calibrated
    with, expressed as positions instead of a prefix slice."""
    for marker in _NEGATION.finditer(sentence):
        if marker.end() > start:
            break  # markers are ordered; this one is past the virtue word
        if start - marker.end() <= _NEGATION_WINDOW:
            return True
    return False


def _carried_virtues(
    sentence: str,
    virtue_res: Mapping[str, "re.Pattern[str]"],
    passed: Sequence[str],
) -> List[str]:
    """The passed virtues this sentence ATTRIBUTES — negation-aware.

    A virtue word under a negation or inverse marker (``pas clair``,
    ``manque de clarté``, ``le moins clair``) states the unit LACKS the
    virtue: that occurrence does not carry. A sentence carries a virtue
    when at least one of its occurrences stands clean.
    """
    carried: List[str] = []
    for virtue in passed:
        rx = virtue_res.get(virtue)
        if rx is None:
            continue
        for match in rx.finditer(sentence):
            if _negated_before(sentence, match.start()):
                continue
            carried.append(virtue)
            break
    return carried


def content_designated_units(
    sentence: str, unit_texts: Mapping[str, str]
) -> List[str]:
    """Unit ids whose text the sentence designates by content.

    A unit is designated when a run of ``>= _DESIGNATION_RUN`` consecutive
    letter tokens of its text appears verbatim in the sentence
    (case-insensitive, punctuation-free on both sides). Deterministic and
    bounded: one pass per unit, no model call — the acceptance path the
    retry's legend makes reachable (« désigne l'unité par ce qu'elle dit »).
    """
    normalised = " " + " ".join(_TOKEN.findall(sentence.lower())) + " "
    designated: List[str] = []
    for unit_id, text in unit_texts.items():
        tokens = _TOKEN.findall(str(text).lower())
        for i in range(max(0, len(tokens) - _DESIGNATION_RUN + 1)):
            run = " ".join(tokens[i : i + _DESIGNATION_RUN])
            if f" {run} " in normalised:
                designated.append(unit_id)
                break
    return designated


def unbacked_localisation_sentences(
    body: str,
    virtue_res: Mapping[str, "re.Pattern[str]"],
    passed_virtues: Sequence[str],
    unit_scores: Mapping[str, Mapping[str, float]],
    unit_texts: Optional[Mapping[str, str]] = None,
) -> List[str]:
    """Measured virtues localised on units the table does not back.

    Returned as the flagged sentences, in order. Empty when there is
    nothing — the check is silent on everything else, including every
    discourse-level virtue claim (the pipeline verdict owns those) and
    every sentence a negation turns into a weakness statement.

    Every returned sentence was READ: it designates units by id or by
    content, and the table contradicts the localisation — or its locative
    designates nothing the state can resolve, which is itself the finding
    (the recorded shape).
    """
    passed = [v for v in passed_virtues if v in virtue_res]
    if not passed or not body:
        return []
    hits: List[str] = []
    for paragraph in re.split(r"\n\s*\n", body):
        for raw in _SENTENCE.findall(paragraph):
            sentence = raw.strip()
            if not sentence or sentence.startswith("#"):
                continue
            carried = _carried_virtues(sentence, virtue_res, passed)
            if not carried:
                continue
            named = list(dict.fromkeys(_UNIT_ID.findall(sentence)))
            content = (
                content_designated_units(sentence, unit_texts)
                if unit_texts
                else []
            )
            designated = list(dict.fromkeys(named + content))
            if not designated and not _LOCATIVE.search(sentence):
                # Discourse-level claim — the verdict's ground, not food.
                continue
            if not designated:
                # A locative onto passages the sentence never designates by
                # id or content: the localisation is unbacked by
                # construction (the recorded shape — « le passage
                # central », passages named by description).
                hits.append(sentence)
                continue
            if any(unit not in unit_scores for unit in designated):
                # The measure never read a designated unit.
                hits.append(sentence)
                continue
            if any(
                float(unit_scores[unit].get(virtue, 0.0)) < _TOP_BAND
                for unit in designated
                for virtue in carried
            ):
                # A designated unit was scored but does not hold the virtue.
                hits.append(sentence)
    return hits


def virtue_localisation_note(count: int, act_label: str = "Acte III") -> str:
    """The motive recorded in the act's ``degraded`` map — empty when clean.

    The render is NOT rewritten behind the reader's back: the reader sees
    the sentence, and the report carries the reason the localisation has no
    measured unit behind it. Counts only, never a quote (#3249). The
    wording is what the check actually judged — no unit at the back of the
    localisation — never a claim that the passage lacks the virtue.
    """
    if count <= 0:
        return ""
    plural = "s" if count > 1 else ""
    return (
        f"{act_label} porte {count} localisation{plural} d'une vertu mesurée "
        "sur des passages sans unité mesurée à l'appui (#3358)"
    )


def virtue_localisation_retry_motif(
    act_label: str,
    flagged_before: int,
    flagged_after: Optional[int] = None,
    failure: str = "",
) -> str:
    """The motive of the bounded writer retry (#3343 shape) — act, counts,
    which draft was kept, never a sentence (#3249).

    ``failure`` names a retry that produced nothing (the ``weave`` contract,
    #1108/#2345): the first draft is kept, and the report says so rather
    than silently pretending the rewrite happened.
    """
    plural = "s" if flagged_before > 1 else ""
    head = (
        f"{act_label} : relance bornée du rédacteur sur {flagged_before} "
        f"localisation{plural} de vertu mesurée sans unité mesurée à "
        "l'appui"
    )
    if failure:
        return (
            f"{head} — la relance n'a rien produit ({failure}) ; le premier "
            "brouillon est conservé."
        )
    if flagged_after is None:
        flagged_after = flagged_before
    kept = "la réécriture" if flagged_after < flagged_before else "le premier brouillon"
    return f"{head} — {flagged_after} après relance ; version conservée : {kept}."


def held_virtues_table(
    passed_virtues: Sequence[str],
    unit_scores: Mapping[str, Mapping[str, float]],
    display: Optional[Mapping[str, str]] = None,
    cap: int = _TABLE_CAP,
) -> str:
    """The per-unit table the base prompt never had — for the retry.

    One line per evaluated unit that holds at least one passed virtue at
    the top band: « ``- arg_13 : clarté 1.0, réfutation constructive 1.0`` ».
    The ids are the WRITER-side keys only until the caller routes the table
    through the relabel seam (#3296) — the writer reads letters with a
    legend, never a raw id. Capped, and the cap is stated — never a silent
    truncation (#1622 idiom). Empty when no unit holds a passed virtue (the
    correction then says so by its emptiness: there is nothing to localise
    on).
    """
    rows: List[str] = []
    for arg_id in sorted(unit_scores):
        held = [
            v
            for v in passed_virtues
            if float(unit_scores[arg_id].get(v, 0.0)) >= _TOP_BAND
        ]
        if not held:
            continue
        names = ", ".join(
            f"{(display or {}).get(v, v)} {float(unit_scores[arg_id][v]):.1f}"
            for v in held
        )
        rows.append(f"- {arg_id} : {names}")
    total = len(rows)
    shown = rows[:cap]
    if total > cap:
        shown.append(
            f"- ({cap} unités listées sur {total} tenant une vertu retenue "
            "au niveau maximal)"
        )
    return "\n".join(shown)
