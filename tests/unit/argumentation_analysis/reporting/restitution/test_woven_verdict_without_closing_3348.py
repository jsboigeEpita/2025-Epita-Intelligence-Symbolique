"""#3348 — the clause-less woven verdict does not escape the removal.

R1133a: the pipeline renders the verdict passage byte for byte (#3345 held),
and in the « Ce qui tient » beat above it the writer wove its own restatement
— « Le discours a un vrai caractère de clarté et il réfute de façon
constructive plus souvent qu'il ne se dérobe » — with no closing clause, so
the #3335 anchor (the clause) had nothing to hold and nothing was removed.
The reader got the verdict twice, the woven copy once without its base and
with a comparison nothing measured.

The repair is a second, independent anchor at the sentence level: the
discourse as grammatical subject, naming every virtue that crossed the bar
AND no virtue the bar rejected. The census on this seat's stored states
(7 states, comment on the issue) measured the literal class at 1 match — a
false positive asserting « clair » with clarté below the bar — and the
bounded class at 0 matches, 0 false positives: a restatement can only copy
what the verdict names, and a sentence asserting a rejected virtue commits
the claim gate's defect, not this removal's, so the rest of its sentence is
not ours to delete.

Everything here is offline: an injectable async LLM stub, real
``UnifiedAnalysisState`` objects, no JVM, no network, no paid call.

Born-red note: every symbol imported at module level already exists on the
father, so the father COLLECTS and these redden on their assertions (the
woven shapes and the verdict passage are spelled out as literals — the
rendering is the contract, not the constant's name; #1647).
"""

from __future__ import annotations

import asyncio

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_conclusion,
    restated_verdict_sentences,
)

_SOURCE_CHARS = 12_000

#: The two virtues the R1133a pass crowned, above the bar.
_VIRTUES = ("clarte", "refutation_constructive")

#: R1133a's shape, synthetic (model prose, quoted in the issue): every passed
#: virtue named, the discourse as subject, no closing clause — and a
#: comparison nothing measured riding the tail.
_WOVEN_R1133A = (
    "### Ce qui tient\n\n"
    "Le discours a un vrai caractère de clarté et il réfute de façon "
    "constructive plus souvent qu'il ne se dérobe.\n\n"
    "### Comment se faire son avis\n\n"
    "Le lecteur gardera ce qui est étayé par le corpus mesuré.\n"
)

#: The census false positive, synthetic: names the ONE passed virtue
#: (redondance) AND a virtue the bar rejected (« clair ») — the claim gate's
#: territory, and its second half carries real content a removal would eat.
_FP_REJECTED_VIRTUE = (
    "### Ce qui tient\n\n"
    "Le discours est donc clair et peu redondant : il organise un récit "
    "simple, celui d'un monde menacé puis restauré.\n\n"
    "### Comment se faire son avis\n\n"
    "Le lecteur gardera ce qui est étayé par le corpus mesuré.\n"
)

#: The DoD's positive control: a « que faire » beat naming the single passed
#: virtue in a one-virtue state — all-passed holds vacuously, only the
#: subject bound keeps it out of the removal.
_QUE_FAIRE = (
    "### Que faire de cette lecture\n\n"
    "Que faire de cette clarté ? L'exiger de chaque passage mesuré.\n\n"
    "### Comment se faire son avis\n\n"
    "Le lecteur gardera ce qui est étayé par le corpus mesuré.\n"
)

_VERDICT_HEADING_LINE = "**Verdict sur les vertus (chiffres du pipeline)**"
_VERDICT_RENDER = (
    "Le discours tient sur clarté (7/8 arguments évalués, 2 unités) ; "
    "réfutation constructive (7/8 arguments évalués, 2 unités). "
    "Aucune autre vertu ne se dit du discours."
)


def _stub_llm(text: str):
    async def _call(_prompt: str) -> str:
        return text

    return _call


def _state(virtues: tuple = _VIRTUES, top_holders: int = 7, evaluated: int = 8):
    """A state whose quality pass crowns ``virtues`` on k/m of the units."""
    state = UnifiedAnalysisState("x" * _SOURCE_CHARS)
    state.add_argument("Le locuteur disqualifie l'adversaire.")
    state.add_argument("Une revendication défendue par un raisonnement causal.")
    quality = {}
    for i in range(1, evaluated + 1):
        top = 1.0 if i <= top_holders else 0.2
        quality[f"arg_{i}"] = {"scores": {virtue: top for virtue in virtues}}
    state.argument_quality_scores = quality
    return state


def _act3(woven: str, state):
    return asyncio.run(build_act3_conclusion(state, llm_callable=_stub_llm(woven)))


class TestTheClauseLessVerdictIsRemoved:
    def test_the_r1133a_sentence_leaves_the_narrative(self):
        """The woven copy is gone — its unmeasured comparison (« plus
        souvent qu'il ne se dérobe ») leaves with it."""
        result = _act3(_WOVEN_R1133A, _state())
        assert "vrai caractère de clarté" not in result.narrative, result.narrative
        assert "plus souvent" not in result.narrative, result.narrative
        assert "il réfute de façon constructive" not in result.narrative

    def test_the_rest_of_the_beats_survive(self):
        result = _act3(_WOVEN_R1133A, _state())
        assert "Le lecteur gardera ce qui est étayé" in result.narrative
        assert _VERDICT_HEADING_LINE in result.narrative
        assert _VERDICT_RENDER in result.narrative

    def test_the_removal_is_recorded_with_counts_never_the_sentence(self):
        """#3249 — the motive is counts only; #3348 reuses the #3335 key."""
        result = _act3(_WOVEN_R1133A, _state())
        motif = result.degraded["act3_verdict_restatement"]
        assert "1" in motif
        assert "clarté" not in motif
        assert "réfute" not in motif


class TestTheBoundHolds:
    def test_a_que_faire_sentence_naming_the_single_virtue_stays(self):
        """DoD positive control: in a one-virtue state « names all passed »
        holds vacuously — the subject bound is what keeps the recommendation
        out of the removal."""
        result = _act3(_QUE_FAIRE, _state(virtues=("clarte",)))
        assert "Que faire de cette clarté ?" in result.narrative, result.narrative
        assert "L'exiger de chaque passage mesuré" in result.narrative

    def test_a_sentence_asserting_a_rejected_virtue_stays(self):
        """The census false positive: « clair » with clarté below the bar is
        the claim gate's defect, not this removal's — and the sentence's
        second half (the narrative arc) is content the reader keeps."""
        result = _act3(_FP_REJECTED_VIRTUE, _state(virtues=("redondance_faible",)))
        assert "peu redondant" in result.narrative, result.narrative
        assert "un monde menacé puis restauré" in result.narrative

    def test_a_partial_naming_survives(self):
        """The #3335 bound, kept: naming SOME passed virtues without the
        closing clause is prose the writer owes the reader. Here clarté
        alone of the two crowned virtues."""
        woven = (
            "### Ce qui tient\n\n"
            "Le discours a un vrai caractère de clarté.\n\n"
            "### Comment se faire son avis\n\n"
            "Le lecteur gardera ce qui est étayé par le corpus mesuré.\n"
        )
        result = _act3(woven, _state())
        assert "vrai caractère de clarté" in result.narrative, result.narrative


class TestTheGraftedPassageIsNeverFood:
    def test_the_detector_skips_the_verdict_passage_paragraph(self):
        """On a final render — removal after the graft, or any direct read —
        the pipeline's own passage is skipped: the woven copy is caught, the
        verdict sentence is not."""
        final_shaped = (
            "Le discours a un vrai caractère de clarté et il réfute de façon "
            "constructive plus souvent qu'il ne se dérobe.\n\n"
            f"{_VERDICT_HEADING_LINE}\n{_VERDICT_RENDER}"
        )
        caught = restated_verdict_sentences(final_shaped, list(_VIRTUES))
        assert len(caught) == 1
        assert "vrai caractère de clarté" in caught[0]
        assert all("Aucune autre vertu" not in s for s in caught)
