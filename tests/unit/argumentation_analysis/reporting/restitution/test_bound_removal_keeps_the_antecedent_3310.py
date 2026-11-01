"""#3310 — the bound remover withdraws the number, it does not orphan the next sentence.

#3134's enforcement deletes every woven sentence that restates a numeric reading
bound (« 10 unités sur 91 »). It removes the WHOLE sentence:

    for _restated in restated_bound_sentences(narrative):
        narrative = narrative.replace(_restated, "").strip()

On the R1127c paid pass (Sonnet 5.5, doc_A) the removed sentence was the
antecedent of the next one: the paragraph opened on

    «  Leur silence est une absence d'examen, non une tenue démontrée. »

A stray leading space, and « Leur » binds nothing — nothing before it says
WHOSE silence. The twin pass R1127b (default thinking, same code) reads
« La plupart des unités n'ont jamais été soumises à la détection de
sophismes. Leur silence est une… »: that head sentence is what disappeared.

The rule is right (#3134) — the writer restates numbers the record carries.
Its ENFORCEMENT is what leaked: cutting the sentence takes the referent with
it, and `.strip()` only trims the ends of the whole text, never the space the
cut leaves behind. Two moves, per the issue:

1. **withdraw the number, keep the sentence**, when the next sentence opens on
   an anaphor — the sentence keeps its subject and the pronoun stays bound;
   an independent successor still takes the whole sentence away (that is the
   #3134 behaviour, and it stays the positive control here);
2. **record each removal in the state** (act, motive, count, never the
   sentence — #3249), on the same ``degraded`` -> ``restitution_acts_degraded``
   channel #3297 uses, filed under the #2046 fabrication-note keys so it
   reaches the appendix archive and never the reader as a repair note.

Everything here is offline: an injectable async LLM stub, real
``UnifiedAnalysisState`` objects, no JVM, no network, no paid call.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution import reading_record
from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    build_act1_framing,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_narrative,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_conclusion,
)

_SOURCE_CHARS = 12_000

#: The R1127c shape, synthetic: a woven bound sentence, then the sentence that
#: points back at it. Nothing here is corpus text.
_BOUND_THEN_ANAPHOR = (
    "La lecture par argument a couvert 10 unités sur 91 du corpus. "
    "Leur silence est une absence d'examen, non une tenue démontrée."
)

#: The positive control: the same bound sentence, then a successor that stands
#: on its own. #3134 keeps working — the whole sentence goes.
_BOUND_THEN_INDEPENDENT = (
    "La lecture par argument a couvert 10 unités sur 91 du corpus. "
    "Le reste du jugement tient sans elle."
)

_WOVEN_ACT2 = (
    "### Ce que le discours dit vraiment\n\n"
    "Le locuteur défend une lecture ordonnée de ses engagements.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    "La position résiste à l'examen croisé des axes.\n\n"
    "### Comment se faire son avis\n\n"
    f"Prudence sur les bornes. {_BOUND_THEN_ANAPHOR}"
)

_WOVEN_ACT3 = (
    "### Ce que le discours dit vraiment\n\n"
    "Le locuteur défend une lecture ordonnée de ses engagements.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    "La position résiste à l'examen croisé des axes.\n\n"
    "### Comment se faire son avis\n\n"
    f"Prudence sur les bornes. {_BOUND_THEN_ANAPHOR}"
)

#: Act I speaks the other bound grammar — a coverage RANGE (#3159), not a
#: unit count. Same defect, same repair.
_WOVEN_ACT1 = (
    "### Le texte\n\n"
    "Le discours analysé est un propos politique d'un locuteur en autorité.\n\n"
    "### La couverture\n\n"
    "L'analyse a porté sur de 6 à 10 unités selon les modules. "
    "Leurs conclusions ne valent donc que pour ce sous-ensemble.\n\n"
    "### Le spectre attendu\n\n"
    "Un auditeur averti doit guetter l'appel à l'autorité pour ce genre.\n\n"
    "QUESTION INTERPRÉTATIVE : Ce discours gagne-t-il l'adhésion par l'autorité ?"
)


def _stub_llm(text: str):
    async def _call(_prompt: str) -> str:
        return text

    return _call


def _state() -> UnifiedAnalysisState:
    """A state that builds a reading record (the acts graft its passage)."""
    state = UnifiedAnalysisState("x" * _SOURCE_CHARS)
    state.add_argument("Le locuteur disqualifie l'adversaire.")
    state.add_argument("Une revendication défendue par un raisonnement causal.")
    state.reading_window_status = {
        "fact_extraction": {"status": "selected", "offset": 0, "window": 3000},
        "fallacy_widenet": {"status": "selected", "offset": 0, "window": 8000},
        "fallacy_one_shot": {"status": "selected", "offset": 0, "window": 8000},
        "fallacy_descent": {"status": "selected", "offset": 0, "window": 500},
        "fallacy_per_argument": {
            "status": "selected",
            "offset": 0,
            "window": 0,
            "units": 10,
            "unit_total": 91,
            "span_lo": 0,
            "span_hi": 0,
        },
    }
    return state


def _act1_state() -> SimpleNamespace:
    """Act I's own stub: stakes + a coverage map with a 6..15 spread."""
    stakes = [
        {"stake_type": "décision", "description": f"point de décision {i}"}
        for i in range(6)
    ]
    coverage = {name: {"k": 6, "N": 90} for name in ("debate", "governance")}
    coverage["synthesis"] = {"k": 15, "N": 90}
    return SimpleNamespace(
        source_metadata={"genre": "discours politique"},
        stakes_and_stakeholders={
            "stakes": stakes,
            "stakeholders": [],
            "rhetorical_register": "délibératif",
            "discursive_arena": "politique",
        },
        identified_arguments={"arg_1": "thèse", "arg_2": "support"},
        analysis_coverage=coverage,
    )


def _act2(woven: str):
    return asyncio.run(build_act2_narrative(_state(), llm_callable=_stub_llm(woven)))


def _act3(woven: str):
    return asyncio.run(build_act3_conclusion(_state(), llm_callable=_stub_llm(woven)))


def _act1(woven: str):
    return asyncio.run(build_act1_framing(_act1_state(), llm_callable=_stub_llm(woven)))


# ============================================================================
# 1. The helper — the number is withdrawn, the sentence that carries it stays
# ============================================================================


class TestTheNumberIsWithdrawnNotTheSentence:
    def test_an_anaphoric_successor_keeps_its_antecedent(self):
        removal = reading_record.remove_restated_bounds(_BOUND_THEN_ANAPHOR)
        text = removal.text
        # The referent survives: « Leur » still has something to point at.
        assert "Leur silence est une absence d'examen" in text
        assert "a couvert" in text  # the head sentence is still there
        # …but the number it restated is gone (#3134 keeps working).
        assert "10 unités sur 91" not in text
        assert "une partie des unités" in text
        # The cut is recorded as a withdrawal, not as a deletion.
        assert removal.withdrawn == 1
        assert removal.removed == 0

    def test_an_independent_successor_still_takes_the_whole_sentence(self):
        # Positive control: the #3134 behaviour is unchanged where it was
        # right — no anaphor to protect, so the woven sentence goes whole.
        removal = reading_record.remove_restated_bounds(_BOUND_THEN_INDEPENDENT)
        assert "10 unités sur 91" not in removal.text
        assert "a couvert" not in removal.text
        assert "Le reste du jugement tient sans elle." in removal.text
        assert removal.removed == 1
        assert removal.withdrawn == 0

    def test_the_cut_leaves_no_leading_space(self):
        # The R1127c fingerprint: the removed head sentence left « \n\n » + a
        # space, so the paragraph opened on a stray blank.
        removal = reading_record.remove_restated_bounds(
            "### Section\n\nUne phrase d'amorce.\n\n" + _BOUND_THEN_INDEPENDENT
        )
        assert not removal.text.startswith(" ")
        assert "\n\n " not in removal.text
        assert "\n\nLe reste" in removal.text

    def test_prose_without_a_restated_bound_is_untouched(self):
        clean = "La lecture par argument a couvert une partie des unités."
        removal = reading_record.remove_restated_bounds(clean)
        assert removal.text == clean
        assert removal.removed == 0
        assert removal.withdrawn == 0


# ============================================================================
# 2. The three acts record the removal — act, motive, count
# ============================================================================


class TestEachActRecordsTheRemoval:
    def test_act1_records_its_range_withdrawal(self):
        result = _act1(_WOVEN_ACT1)
        assert "act1_bound_restatement" in result.degraded
        assert "de 6 à 10 unités" not in result.narrative
        assert "Leurs conclusions" in result.narrative

    def test_act2_records_its_bound_withdrawal(self):
        result = _act2(_WOVEN_ACT2)
        assert "act2_bound_restatement" in result.degraded
        # The WOVEN restatement is gone; the record's own passage still carries
        # the figure, where it sits under its site label (#3134).
        assert "a couvert 10 unités sur 91" not in result.narrative
        assert "une partie des unités du corpus" in result.narrative
        assert "Leur silence" in result.narrative

    def test_act3_records_its_bound_withdrawal(self):
        result = _act3(_WOVEN_ACT3)
        assert "act3_bound_restatement" in result.degraded
        assert "a couvert 10 unités sur 91" not in result.narrative
        assert "une partie des unités du corpus" in result.narrative
        assert "Leur silence" in result.narrative

    def test_the_motive_carries_the_counts_and_never_the_sentence(self):
        # #3249 — a motive is a code literal with counts, never a quote of the
        # prose. An auditor reads WHAT changed and HOW MANY, not the render.
        result = _act2(_WOVEN_ACT2)
        motif = result.degraded["act2_bound_restatement"]
        assert "1" in motif
        assert "couvert" not in motif
        assert "silence" not in motif

    def test_the_motif_never_reaches_the_reader_as_a_repair_note(self):
        # #2046 — the fabrication-note keys are archived in the appendix and
        # dropped from the reader blockquote. Both twins must agree.
        from argumentation_analysis.reporting.restitution import (
            appendix,
            pipeline_adapter,
        )

        key = "act2_bound_restatement"
        assert key in appendix._FABRICATION_NOTE_KEYS
        assert key in pipeline_adapter._FABRICATION_NOTE_KEYS
