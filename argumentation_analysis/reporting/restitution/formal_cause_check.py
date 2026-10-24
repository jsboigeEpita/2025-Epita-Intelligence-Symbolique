"""Deterministic cause-attribution check: whose clash a formal constat may state (#3237).

## The gap this closes

#3107/#3122 gave every formal inconsistency a RECORDED cause, and Act III's
prompt carried the rule that binds the prose to it. Act II received the cause
on its evidence lines (« contradiction entre unités sources … — locuteurs non
documentés par ce run ») but not the rule — and it is the act that misstated
the cause (R1110c, doc_A, code ``4101cdc26``): Act II described the formal
contradictions as « le point où les deux voix se heurtent », precisely the
cause the record says it cannot establish, while Act III and the narrative
synthesis said the opposite. The report contradicted itself on why the solver
found an inconsistency.

The repair is two-handed, as the family's previous fixes were:

1. **The rule** — ``FORMAL_CAUSE_NAMING_RULE`` (``fol_cause.py``, the cause
   vocabulary's one home) is imported by BOTH acts' prompts. A field without
   its reader on one of its two surfaces is how the defect happened.
2. **The guarantee** — a rule the writer can break is not a guarantee (the
   #3159 lesson). This module is the post-render detector: when every
   recorded formal cause in the state is something other than
   ``between_voices``, a sentence that ties a formal contradiction to voices
   or speakers clashing is flagged, FAIL band.

## Marker, and why it is this narrow

The figure: a « deux voix / deux locuteurs » subject carrying a clash verb
(``heurt* / affront* / oppos* / clash* / confront* / entrechoqu*``) in the
same sentence. The tie to a FORMAL constat: a formal noun
(``contradict* / inconsist* / insatisfais* / incompatib*``) in the same
sentence — the direct shape (« deux contradictions … : le point où les deux
voix se heurtent ») — or in the immediately preceding sentence, the anaphoric
shape French prose actually produces (« Le solveur relève une contradiction.
C'est le point où les deux voix se heurtent. »). The gate: at least one
stated cause over the refuted PL/FOL records, and none of them
``between_voices`` — when the run documents two voices, « contradiction entre
voix » is the right sentence and this check says nothing (anti-pendulum: the
voice-clash cause is deleted nowhere, the word « voix » is banned nowhere, and
the two-voice caution on the speaker — legitimate and present in every act —
carries no formal noun and never flags).

Measured on the six stored local renders (12 act bodies) before settling:
0 flags at every strictness level, 0 false positives — no local state states
a formal cause, so the gate never opens; the with-causes corpus (237 act
bodies, 81 states) lives on the coordinator's seat and is the DoD replay.

## Honesty contract (#1019)

The check only ever reports; it never needs an LLM. With no state, no stated
cause, or a ``between_voices`` cause recorded, it returns PASS silently. The
producer-side strip (Act II, the #1605 removal shape) runs BEFORE the state
is persisted — this detector is defense in depth for any render path that
bypasses it, and for Act III.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .readability_gate import GateVerdict

# Sentence split on terminal punctuation followed by an opening capital,
# quote or parenthesis — the same shape the reading checks use.
_SENT_SPLIT = re.compile(r"(?<=[.!?;])\s+(?=[A-ZÀ-ÖØ-Þ«\"'(])")

# The « two voices » figure. Deliberately narrow: a rhetorical voice clash
# named with any other wording (« les orateurs débattent ») is legitimate
# prose this check must not police.
_TWO_VOICES = r"(?:deux|2)\s+(?:voix|locuteurs?|speakers?|orateurs?)"
_CLASH_VERBS = r"(?:heurt\w*|affront\w*|oppos\w*|clash\w*|confront\w*|entrechoqu\w*)"
_VOICE_CLASH_FIGURE = re.compile(
    rf"{_TWO_VOICES}.{{0,120}}?{_CLASH_VERBS}", re.IGNORECASE | re.DOTALL
)

# The formal-constat vocabulary that ties the figure to a solver finding.
_FORMAL_NOUN = re.compile(
    r"(?:contradict\w*|inconsist\w*|insatisfais\w*|incompatib\w*)", re.IGNORECASE
)


def _field(state: Any, key: str) -> Any:
    """Read a state field from a Mapping (renderer) or attribute (state)."""
    if state is None:
        return None
    if isinstance(state, Mapping):
        return state.get(key)
    return getattr(state, key, None)


def _verdict(record: Dict[str, Any]) -> Optional[bool]:
    """Refuted-or-not for a PL/FOL record — both writer keys, never None→False.

    PL's canonical writer key is ``satisfiable`` (shared_state.py:801); FOL's
    is ``consistent``; the legacy reader key ``consistent`` maps to the same
    satisfiability semantics (#1151/#1153). ``None`` stays ``None`` (#1019).
    """
    sat = record.get("satisfiable")
    if sat is None:
        sat = record.get("consistent")
    return sat if isinstance(sat, bool) else None


def stated_formal_causes(state: Any) -> List[str]:
    """Every cause class the run RECORDED on a refuted PL/FOL theory, in order.

    Empty when no refuted record stated one — the check then asserts nothing
    (there is no recorded cause for the prose to contradict).
    """
    causes: List[str] = []
    for key in ("propositional_analysis_results", "fol_analysis_results"):
        records = _field(state, key)
        if not isinstance(records, list):
            continue
        for r in records:
            if not isinstance(r, dict) or _verdict(r) is not False:
                continue
            cause = r.get("consistency_cause")
            if isinstance(cause, dict) and cause.get("cause"):
                causes.append(str(cause["cause"]))
    return causes


def voice_clash_cause_sentences(body: str, state: Any) -> List[str]:
    """In-text sentences tying a formal contradiction to voices clashing.

    Returned as exact slices of ``body`` (the strip removes them verbatim).
    Empty when the gate does not open: no stated cause, or a recorded
    ``between_voices`` cause (the run then documents the two voices, and the
    clash sentence is the honest one).
    """
    causes = stated_formal_causes(state)
    if not causes or "between_voices" in causes:
        return []
    sentences = _SENT_SPLIT.split(body)
    hits: List[str] = []
    for i, sentence in enumerate(sentences):
        if not _VOICE_CLASH_FIGURE.search(sentence):
            continue
        # the tie: a formal noun in the same sentence, or in the one right
        # before it (French anaphora — « C'est le point où … » refers back).
        if _FORMAL_NOUN.search(sentence) or (
            i > 0 and _FORMAL_NOUN.search(sentences[i - 1])
        ):
            hits.append(sentence.strip())
    return hits


def strip_voice_clash_cause_sentences(
    narrative: str, state: Any
) -> Tuple[str, List[str]]:
    """#1605 removal shape for the producer side: the sentences go, logged.

    The act's evidence lines already carry the record's own cause phrase, so
    nothing true is lost — the same contract as the #3134 bound restatements.
    """
    removed = voice_clash_cause_sentences(narrative, state)
    if not removed:
        return narrative, []
    out = narrative
    for sentence in removed:
        out = out.replace(sentence, "")
    return out.strip(), removed


def check_formal_cause_attribution(body: str, state: Any) -> GateVerdict:
    """Post-render defense in depth: FAIL when the prose misstates the cause.

    A sentence that ties a formal contradiction to voices clashing, when every
    recorded formal cause is something other than ``between_voices``, is the
    report contradicting its own record — the same gravity as the
    ``check_factual_consistency`` prose theatre (#1316). Silent PASS whenever
    the gate does not open (no state, no stated cause, ``between_voices``
    recorded).
    """
    flagged = voice_clash_cause_sentences(body, state) if body else []
    if not flagged:
        return GateVerdict(band="PASS", reasons=[])
    causes = stated_formal_causes(state)
    recorded = ", ".join(sorted(set(causes)))
    reasons = [
        "une contradiction formelle est prête à un heurt de voix alors que le "
        f"run enregistre autre chose ({recorded}) — la cause enregistrée est "
        "la seule à dire : « " + sentence[:120] + " » (#3237)"
        for sentence in flagged
    ]
    return GateVerdict(band="FAIL", reasons=reasons)
