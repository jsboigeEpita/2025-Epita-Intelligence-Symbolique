"""#3547 — read the counterfactual axis from the Act III render, deterministically.

The counting rule that once declared « 1 of 9 rendered » read labels and
markers the render structurally cannot carry: the Act III prompt forbids
echoing the axis label, the arg ids and the pipeline vocabulary, so a render
CAN only carry the fact in paraphrased French. The coordinator's semantic
re-read of the 6 recorded renders (State of 18/11, comment 6972562252) found
the dependence in 5/5 renders that had an entry, the consequence explicit in
2/5 — but as ONE reader's judgment, not a reproducible count.

This instrument is that reading as a rule. It reads the render's analysis
prose (the sections before the run-metadata markers) and counts three forms,
each measured on the recorded renders themselves:

- **Dependence** — a support relation between two discourse objects:
  ``A soutient B`` (verb; the thesis ``il soutient que …`` is excluded, a
  thesis is not a relation, and so is the past participle ``soutenue par``),
  ``s'appuie sur`` (reflexive), ``repose sur`` (including the
  comma-interrupted ``repose, dit-il, sur``). Run-metadata sentences (any
  sentence carrying the word « run ») are excluded: the run's base is not a
  document-internal support — measured false positive, « le socle du run
  repose sur des unités ».
- **Sole support** — the render names the relation as the dependent's only
  one: ``à lui seul``, ``seul soutien``, ``seule justification``,
  ``son seul appui``.
- **Consequence** — the counterfactual half, on a counterfactual operator
  only: the withdrawal conditional (``si … disparaît, … perd …``) or the
  conditional-weakening form (``fragilisation … aurait des effets``). The
  present-tense ``fragilise``/``affaiblit`` and the bare noun ``fragilité``
  do NOT count — a present vulnerability is not the withdrawal chain; this
  distinction is the judgment call the rule freezes, and it reproduces the
  coordinator's table on all six recorded renders.

Alongside the render reading, the state side is censused: the counterfactual
entries the writer had (``jtms_counterfactual_withdrawals``), so one row
shows what there was to render and what the render carries.

Privacy: prints counts, booleans and form names only, under the label it was
given — no sentence of the render, no document id. States are passed by path.

Usage (the label mapping stays in the invocation, the output carries it)::

    python scripts/panel/read_counterfactual_render_3547.py \
        --pair c18_doc_G=<path/to/state_full_….json> …
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import List, Tuple

# The render's analysis prose ends where the run metadata begins. Both
# markers measured on the recorded renders.
_SCOPE_MARKERS = ("**Verdict sur les vertus", "**Bornes de lecture du run")

# A sentence about the run (its base, its coverage) is metadata, not
# document-internal analysis. Measured false positive to exclude: a rests-on
# sentence whose subject is the run's base.
_RUN_WORD = re.compile(r"\brun\b", re.IGNORECASE)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Both apostrophe shapes occur across renders (straight and typographic).
_APOS = "['’`]"

# --- Dependence forms ------------------------------------------------------
# The support verb between two discourse objects. The lookahead excludes the
# thesis use (« il soutient que … ») — a thesis is not a support relation.
_SUPPORT_VERB = re.compile(r"\bsoutien(?:t|nent)\b(?!\s+que\b)", re.IGNORECASE)
_RESTS_ON_REFLEXIVE = re.compile(rf"\bs{_APOS}appuie\b", re.IGNORECASE)
# « repose sur », including the comma-interrupted « repose, dit-il, sur »
# (measured on a recorded render).
_RESTS_ON = re.compile(r"\brepose\b[^.;!?]{0,24}\bsur\b", re.IGNORECASE)

_DEPENDENCE_PATTERNS: Tuple[Tuple[str, re.Pattern], ...] = (
    ("support_verb", _SUPPORT_VERB),
    ("rests_on_reflexive", _RESTS_ON_REFLEXIVE),
    ("rests_on", _RESTS_ON),
)

# --- Sole support ----------------------------------------------------------
_SOLE_SUPPORT = re.compile(
    r"à lui seul|à elle seule|seul soutien|unique soutien"
    r"|seule justification|son seul appui|le seul appui",
    re.IGNORECASE,
)

# --- Consequence forms -----------------------------------------------------
# The withdrawal conditional: a si-clause naming the disappearance or the
# withdrawal, and a fall effect in the same sentence.
_WITHDRAWAL = re.compile(
    rf"\b(?:si|lorsque|quand)\b[^.;!?]{{0,80}}?"
    rf"(?:dispara\w*|est retiré|était retiré|serait retiré"
    rf"|venait à disparaître|n{_APOS}existait plus)",
    re.IGNORECASE,
)
_FALL_EFFECT = re.compile(
    rf"\bperd\w*\b|\btombe\w*\b|s{_APOS}effondre|effondr\w*|ne tiendrait plus",
    re.IGNORECASE,
)
# The conditional-weakening form: the fragilisation family AND a conditional
# effect verb in the same sentence. Present tense (« cela fragilise ») and
# the bare noun (« une fragilité ») are deliberately outside — a present
# vulnerability is not the withdrawal chain.
_WEAKENING_FAMILY = re.compile(r"\bfragilis\w+|\baffaibl\w+", re.IGNORECASE)
_CONDITIONAL_EFFECT = re.compile(
    r"\baurait\b|\bauraient\b|\bengendrerait\b|\bprovoquerait\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RenderReading:
    """One render's reading: what the render carries, and what it had."""

    entries: int
    dependence: bool
    sole_support: bool
    consequence: bool
    dep_forms: Tuple[str, ...]
    cons_forms: Tuple[str, ...]
    dep_relations: int


def _analysis_prose(render: str) -> str:
    """The render's analysis sections, before the run metadata markers.

    Section titles are dropped: a title may carry the support verb as a
    label (« ce que l'appel soutient réellement », measured on a recorded
    render) without stating any relation between two discourse objects.
    """
    cut = len(render)
    for marker in _SCOPE_MARKERS:
        pos = render.find(marker)
        if pos != -1 and pos < cut:
            cut = pos
    body = render[:cut]
    lines = [line for line in body.splitlines() if not line.lstrip().startswith("#")]
    return "\n".join(lines)


def _sentences(prose: str) -> List[str]:
    return [s for s in _SENTENCE_SPLIT.split(prose) if s.strip()]


def read_render(render: str) -> RenderReading:
    """Read one Act III render with the deterministic rule."""
    sentences = [
        s for s in _sentences(_analysis_prose(render)) if not _RUN_WORD.search(s)
    ]
    dep_forms: List[str] = []
    cons_forms: List[str] = []
    dep_relations = 0
    sole_support = False
    consequence = False
    for sentence in sentences:
        carries_relation = False
        for name, pattern in _DEPENDENCE_PATTERNS:
            matches = pattern.findall(sentence)
            if matches:
                carries_relation = True
                if name not in dep_forms:
                    dep_forms.append(name)
                dep_relations += len(matches)
        carries_fall = bool(_FALL_EFFECT.search(sentence))
        # The sole marker counts only beside a relation or a fall in the
        # same sentence: « soutient à lui seul » (relation side) or « perd
        # sa seule justification » (fall side). The sufficiency idiom —
        # « ne suffit pas, à elle seule, à établir », measured on a
        # recorded render — names no support and must not fire.
        if _SOLE_SUPPORT.search(sentence) and (carries_relation or carries_fall):
            sole_support = True
        if _WITHDRAWAL.search(sentence) and carries_fall:
            consequence = True
            if "withdrawal_conditional" not in cons_forms:
                cons_forms.append("withdrawal_conditional")
        if _WEAKENING_FAMILY.search(sentence) and _CONDITIONAL_EFFECT.search(sentence):
            consequence = True
            if "conditional_weakening" not in cons_forms:
                cons_forms.append("conditional_weakening")
    return RenderReading(
        entries=0,
        dependence=dep_relations > 0,
        sole_support=sole_support,
        consequence=consequence,
        dep_forms=tuple(dep_forms),
        cons_forms=tuple(cons_forms),
        dep_relations=dep_relations,
    )


def read_counterfactual_state(state_path: Path, render: str) -> RenderReading:
    """Census the writer's counterfactual entries beside the render reading."""
    state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    entries = state.get("jtms_counterfactual_withdrawals") or []
    return replace(read_render(render), entries=len(entries))


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read the counterfactual axis from recorded Act III renders."
    )
    parser.add_argument(
        "--pair",
        action="append",
        required=True,
        metavar="LABEL=STATE_JSON",
        help="an opaque label and the recorded state's path; the render is "
        "read from the state's act3_conclusion",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit one JSON object per pair"
    )
    args = parser.parse_args(argv)

    dep_count = 0
    sole_count = 0
    cons_count = 0
    for pair in args.pair:
        label, _, raw_path = pair.partition("=")
        state = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        reading = read_counterfactual_state(
            Path(raw_path), render=state.get("act3_conclusion") or ""
        )
        dep_count += reading.dependence
        sole_count += reading.sole_support
        cons_count += reading.consequence
        if args.json:
            print(
                json.dumps(
                    {
                        "label": label,
                        "entries": reading.entries,
                        "dependence": reading.dependence,
                        "sole_support": reading.sole_support,
                        "consequence": reading.consequence,
                        "dep_forms": list(reading.dep_forms),
                        "cons_forms": list(reading.cons_forms),
                        "dep_relations": reading.dep_relations,
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(
                f"{label}: entries={reading.entries} "
                f"dep={'yes' if reading.dependence else 'no'} "
                f"sole={'yes' if reading.sole_support else 'no'} "
                f"cons={'yes' if reading.consequence else 'no'} "
                f"dep_relations={reading.dep_relations} "
                f"forms={','.join(reading.dep_forms + reading.cons_forms) or '-'}"
            )
    print(
        f"TOTAL: dependence on {dep_count} of {len(args.pair)} pairs, "
        f"sole support on {sole_count}, consequence on {cons_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
