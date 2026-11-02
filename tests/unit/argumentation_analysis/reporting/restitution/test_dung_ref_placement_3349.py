# -*- coding: utf-8 -*-
"""#3349 — a Dung annex ref rides the sentence it proves.

Paid pass R1133a (``doc 8fa89437_ext1``, main ``30ec9a3cb``): Act II put
the Dung annex ref on the FIRST-ORDER/MODAL sentence — a reader following
it lands in the attack-graph annex, which holds no FOL or modal material.
The #1914 citation contract (``annex_ref_rule``) was prompt-only; nothing
checked where a ref landed.

The repair is the family's two-handed shape: the deterministic
``move_misplaced_dung_refs`` (this module's target) wired into Act II's
assembly, and its motif filed under the #2046 fabrication-note keys.

Scope — narrow on purpose. The dispatch's coarse census (ref sentence with
no graph keyword) mostly caught prose that talks about the graph in other
words; the conjunction the recorded defect has and the false positives do
not is: another formal axis named AND no graph vocabulary. Only that shape
moves (to the paragraph's nearest preceding graph sentence, else the
nearest following, else the ref is dropped).

Synthetic vocabularies only — no corpus text, opaque ids only.
"""

from __future__ import annotations

import asyncio

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_narrative,
)
from argumentation_analysis.reporting.restitution.dung_ref_placement import (
    dung_ref_placement_motif,
    move_misplaced_dung_refs,
)

#: The recorded shape, synthetic: two graph sentences, then the formal-axis
#: sentence wearing the annex ref it does not prove.
_RECORDED_PARAGRAPH = (
    "Le graphe d'attaque est construit à partir de 40 arguments retenus "
    "sur 90 unités identifiées. Il fragilise trois d'entre eux. "
    "Les tests de théories du premier ordre et modale n'ont rien "
    "distingué (voir Annexe Dung[preferred])."
)

#: The ref already where it proves something: byte-identical passthrough.
_REF_ON_GRAPH = (
    "Le graphe d'attaque est construit à partir de 40 arguments retenus "
    "sur 90 unités identifiées (voir Annexe Dung[preferred]). "
    "Les tests de théories du premier ordre et modale n'ont rien distingué."
)

#: The coarse-census false-positive class, synthetic: no formal axis named,
#: no graph keyword either — prose about the graph in other words.
_FALSE_POSITIVES = [
    "C'est une réorganisation du matériau, non une vérification "
    "indépendante (voir Annexe Dung[preferred]).",
    "Une thèse opposée n'y garde aucune assise (voir Annexe Dung[alpha]).",
]


class TestTheRefRidesTheSentenceItProves:
    def test_the_recorded_shape_moves_the_ref_to_the_nearest_graph_sentence(self):
        """Born red on main: no check existed, the ref stayed on the FOL
        sentence. It moves to the nearest PRECEDING graph sentence (« Il
        fragilise… »), the minimal displacement."""
        text, moved, dropped = move_misplaced_dung_refs(_RECORDED_PARAGRAPH)
        assert moved == 1 and dropped == 0
        assert (
            "Il fragilise trois d'entre eux (voir Annexe Dung[preferred])." in text
        ), text
        assert "rien distingué." in text, text
        assert "rien distingué (voir" not in text, text

    def test_a_ref_already_on_the_graph_sentence_stays_byte_identical(self):
        """Positive control: the ref where it belongs — nothing moves."""
        text, moved, dropped = move_misplaced_dung_refs(_REF_ON_GRAPH)
        assert (moved, dropped) == (0, 0)
        assert text == _REF_ON_GRAPH

    def test_the_coarse_census_false_positives_stay_put(self):
        """The locally read false-positive class: a ref sentence with no
        formal axis named is NOT displaced, whatever keywords it lacks."""
        for sentence in _FALSE_POSITIVES:
            text, moved, dropped = move_misplaced_dung_refs(sentence)
            assert (moved, dropped) == (0, 0), sentence
            assert text == sentence, sentence

    def test_no_graph_sentence_in_the_paragraph_drops_the_ref(self):
        """A paragraph with no graph sentence cannot host the ref: it is
        dropped, the sentence itself stays."""
        text, moved, dropped = move_misplaced_dung_refs(
            "Les tests de théories du premier ordre et modale n'ont rien "
            "distingué (voir Annexe Dung[preferred])."
        )
        assert moved == 0 and dropped == 1
        assert "Annexe Dung" not in text, text
        assert (
            "Les tests de théories du premier ordre et modale n'ont rien distingué."
            in text
        )

    def test_the_paragraph_scope_does_not_leak_across_paragraphs(self):
        """A graph sentence in ANOTHER paragraph does not receive the ref —
        the move is paragraph-scoped, so the ref anchors stay local."""
        text, moved, dropped = move_misplaced_dung_refs(
            "Le graphe d'attaque est construit à partir de 40 arguments.\n\n"
            "Les tests de théories du premier ordre et modale n'ont rien "
            "distingué (voir Annexe Dung[preferred])."
        )
        assert moved == 0 and dropped == 1
        assert "construit à partir" in text and "Annexe Dung" not in text, text

    def test_the_motif_carries_counts_and_never_the_sentence(self):
        """#3249 — act and counts, never a quote of the prose."""
        motif = dung_ref_placement_motif("Acte II", 1, 1)
        assert motif.startswith("Acte II : ")
        assert "1" in motif
        assert "distingué" not in motif
        assert "premier ordre" not in motif


# ============================================================================
# 2. The wiring — Act II's assembly runs the check and records the motif
# ============================================================================


def _stub_llm(text: str):
    async def _call(_prompt: str) -> str:
        return text

    return _call


_WOVEN_ACT2 = (
    "### Ce que le discours dit vraiment\n\n"
    "Le locuteur défend une lecture ordonnée de ses engagements.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    f"{_RECORDED_PARAGRAPH}\n\n"
    "### Comment se faire son avis\n\n"
    "Prudence sur les bornes."
)

_WOVEN_ACT2_CLEAN = (
    "### Ce que le discours dit vraiment\n\n"
    "Le locuteur défend une lecture ordonnée de ses engagements.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    "Le graphe d'attaque est construit à partir de 40 arguments.\n\n"
    "### Comment se faire son avis\n\n"
    "Prudence sur les bornes."
)

_SOURCE_CHARS = 12_000


def _state() -> UnifiedAnalysisState:
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


def _act2(woven: str):
    return asyncio.run(build_act2_narrative(_state(), llm_callable=_stub_llm(woven)))


class TestActTwoRecordsThePlacement:
    def test_the_woven_misplaced_ref_is_moved_by_the_assembly(self):
        """Born red on main: the assembly returned the writer's text as
        woven — the ref stayed on the FOL sentence."""
        result = _act2(_WOVEN_ACT2)
        assert "fragilise trois d'entre eux (voir Annexe Dung[preferred])" in (
            result.narrative
        ), result.narrative
        assert "rien distingué (voir" not in result.narrative
        assert "act2_dung_ref_placement" in result.degraded

    def test_a_clean_weave_records_nothing(self):
        result = _act2(_WOVEN_ACT2_CLEAN)
        assert "act2_dung_ref_placement" not in result.degraded

    def test_the_motif_is_archived_never_reader_facing(self):
        """#2046 — the fabrication-note keys are archived in the appendix
        and dropped from the reader blockquote. Both twins must agree."""
        from argumentation_analysis.reporting.restitution import (
            appendix,
            pipeline_adapter,
        )

        key = "act2_dung_ref_placement"
        assert key in appendix._FABRICATION_NOTE_KEYS
        assert key in pipeline_adapter._FABRICATION_NOTE_KEYS
